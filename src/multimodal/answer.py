"""Answer generation for multimodal RAG.

Retrieve mixed text/table/image chunks, then build a prompt where text/tables go in as text
and figures go in as ACTUAL images (Gemini reads them). The model can therefore answer from a
chart's pixels (e.g. "which category was most common?"). The `trace` returns the evidence used,
including the figure images (base64) for the UI.
"""

import base64
import logging
import time

from llm import Image, active_generation_model, get_generation_provider

from .retrieval import retrieve


logger = logging.getLogger("multimodal.answer")

INPUT_USD_PER_1M = 0.30
OUTPUT_USD_PER_1M = 2.50


class MultimodalAnswerError(RuntimeError):
    """Multimodal answer generation failed at the provider boundary."""


def _build_contents(question, chunks, max_images):
    """Assemble the multimodal prompt: numbered text/table facts + figure images (as Image parts).

    `max_images` comes from the active provider (tight free-tier caps allow fewer images).
    """
    parts = []
    lines = [
        "Answer the question using ONLY the numbered evidence below (text, tables, and "
        "figures). Cite what you use inline like [1]. If it isn't answerable, say so.\n"
    ]
    image_count = 0
    for n, chunk in enumerate(chunks, start=1):
        if chunk.kind == "image" and image_count < max_images and chunk.image_b64:
            lines.append(f"[{n}] Figure — {chunk.context} (see image):")
            parts.append("\n".join(lines)); lines = []
            parts.append(Image(data=base64.b64decode(chunk.image_b64), mime="image/png"))
            image_count += 1
        else:
            label = "Table" if chunk.kind == "table" else "Text"
            lines.append(f"[{n}] {label} (p{chunk.page}):\n{chunk.text}")
    lines.append(f"\nQuestion: {question}\nAnswer:")
    parts.append("\n".join(lines))
    return parts


# Output budget for the vision call: one image is ~2000 input tokens, so ~5000 output keeps
# the request under an 8000 TPM cap while giving a reasoning model room to read + answer.
VISION_MAX_TOKENS = 5000


def _generate(contents):
    """Generate (vision) via the configured provider. Returns (text, usage-dict)."""
    result = get_generation_provider().generate(contents, max_tokens=VISION_MAX_TOKENS)
    return result.text, {
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "total_tokens": result.total_tokens,
    }


def answer(question, k=5):
    """Retrieve cross-modally and generate a cited answer that can read figures.

    Any failure (embedding, generation) is wrapped as MultimodalAnswerError.
    """
    start = time.perf_counter()
    try:
        chunks = retrieve(question, k=k)
        max_images = get_generation_provider().max_images
        text, usage = _generate(_build_contents(question, chunks, max_images))
    except Exception as error:
        raise MultimodalAnswerError(f"multimodal answer failed: {error}") from error
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    trace = [
        {
            "n": n,
            "kind": chunk.kind,
            "source": chunk.source,
            "page": chunk.page,
            "text": chunk.text,
            "context": chunk.context,
            "image_b64": chunk.image_b64,  # figures: shown in the UI
        }
        for n, chunk in enumerate(chunks, start=1)
    ]

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
            "model": active_generation_model(),
        },
    }
