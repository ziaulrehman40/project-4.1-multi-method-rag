"""Answer generation for multimodal RAG.

Retrieve mixed text/table/image chunks, then build a prompt where text/tables go in as text
and figures go in as ACTUAL images (Gemini reads them). The model can therefore answer from a
chart's pixels (e.g. "which category was most common?"). The `trace` returns the evidence used,
including the figure images (base64) for the UI.
"""

import base64
import logging
import os
import time

from django.conf import settings
from google import genai
from google.genai import types

from .retrieval import retrieve


logger = logging.getLogger("multimodal.answer")

MODEL = settings.GEMINI_MODEL  # gemini-2.5-flash-lite (vision-capable, verified)
MAX_RETRIES = 4
BASE_DELAY_SECONDS = 2.0
MAX_IMAGES = 3  # cap figures passed to the model (cost/context)

INPUT_USD_PER_1M = 0.30
OUTPUT_USD_PER_1M = 2.50


class MultimodalAnswerError(RuntimeError):
    """Multimodal answer generation failed at the provider boundary."""


def _build_contents(question, chunks):
    """Assemble the multimodal prompt: numbered text/table facts + figure images as Parts."""
    parts = []
    lines = [
        "Answer the question using ONLY the numbered evidence below (text, tables, and "
        "figures). Cite what you use inline like [1]. If it isn't answerable, say so.\n"
    ]
    image_count = 0
    for n, chunk in enumerate(chunks, start=1):
        if chunk.kind == "image" and image_count < MAX_IMAGES and chunk.image_b64:
            lines.append(f"[{n}] Figure — {chunk.context} (see image):")
            parts.append("\n".join(lines)); lines = []
            parts.append(
                types.Part.from_bytes(
                    data=base64.b64decode(chunk.image_b64), mime_type="image/png"
                )
            )
            image_count += 1
        else:
            label = "Table" if chunk.kind == "table" else "Text"
            lines.append(f"[{n}] {label} (p{chunk.page}):\n{chunk.text}")
    lines.append(f"\nQuestion: {question}\nAnswer:")
    parts.append("\n".join(lines))
    return parts


def _generate(contents):
    """One Gemini (vision) call, retrying transient 503/429. Returns (text, usage)."""
    delay = BASE_DELAY_SECONDS
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            response = client.models.generate_content(model=MODEL, contents=contents)
            usage = response.usage_metadata
            return (response.text or ""), {
                "input_tokens": getattr(usage, "prompt_token_count", 0) or 0,
                "output_tokens": getattr(usage, "candidates_token_count", 0) or 0,
                "total_tokens": getattr(usage, "total_token_count", 0) or 0,
            }
        except Exception as error:
            last_error = error
            if attempt < MAX_RETRIES - 1:
                logger.warning("multimodal.answer.retry attempt=%d error=%s", attempt + 1, error)
                time.sleep(delay)
                delay *= 2
    raise last_error


def answer(question, k=5):
    """Retrieve cross-modally and generate a cited answer that can read figures."""
    chunks = retrieve(question, k=k)
    trace = [
        {
            "n": n,
            "kind": chunk.kind,
            "page": chunk.page,
            "text": chunk.text,
            "context": chunk.context,
            "image_b64": chunk.image_b64,  # figures: shown in the UI
        }
        for n, chunk in enumerate(chunks, start=1)
    ]

    start = time.perf_counter()
    try:
        text, usage = _generate(_build_contents(question, chunks))
    except Exception as error:
        raise MultimodalAnswerError(f"multimodal answer generation failed: {error}") from error
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    est_cost = (
        usage["input_tokens"] / 1_000_000 * INPUT_USD_PER_1M
        + usage["output_tokens"] / 1_000_000 * OUTPUT_USD_PER_1M
    )
    return {
        "answer": text,
        "trace": trace,
        "metrics": {
            **usage,
            "latency_ms": latency_ms,
            "est_cost_usd": round(est_cost, 6),
            "evidence_used": len(trace),
            "model": MODEL,
        },
    }
