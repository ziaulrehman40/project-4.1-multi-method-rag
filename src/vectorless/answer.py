"""Answer generation for vectorless (reasoning-based) RAG.

Navigate the document tree to select sections, read ONLY those sections' content, and
generate a cited answer. The `trace` is the navigation path — which sections were opened —
each identified by its breadcrumb path (the citation).
"""

import logging
import os
import time

from django.conf import settings
from google import genai

from .navigation import navigate


logger = logging.getLogger("vectorless.answer")

MODEL = settings.GEMINI_MODEL
MAX_RETRIES = 4
BASE_DELAY_SECONDS = 2.0

# Approximate Gemini Flash rates (USD per 1M tokens); shown as an estimate only.
INPUT_USD_PER_1M = 0.30
OUTPUT_USD_PER_1M = 2.50


class VectorlessAnswerError(RuntimeError):
    """Vectorless answer generation failed at the provider boundary."""


def _generate(prompt):
    """One Gemini call, retrying transient 503/429 with backoff. Returns (text, usage)."""
    delay = BASE_DELAY_SECONDS
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            response = client.models.generate_content(model=MODEL, contents=prompt)
            usage = response.usage_metadata
            return (response.text or ""), {
                "input_tokens": getattr(usage, "prompt_token_count", 0) or 0,
                "output_tokens": getattr(usage, "candidates_token_count", 0) or 0,
                "total_tokens": getattr(usage, "total_token_count", 0) or 0,
            }
        except Exception as error:
            last_error = error
            if attempt < MAX_RETRIES - 1:
                logger.warning("vectorless.answer.retry attempt=%d error=%s", attempt + 1, error)
                time.sleep(delay)
                delay *= 2
    raise last_error


def _build_prompt(question, sections):
    context = "\n\n".join(
        f"[{n}] {section.path}\n{section.content}" for n, section in enumerate(sections, start=1)
    )
    return (
        "Answer the question using ONLY the numbered sections below. Cite the sections you "
        "use inline with their number, like [1]. If they do not answer the question, say you "
        "cannot find it.\n\n"
        f"Sections:\n{context}\n\nQuestion: {question}\nAnswer:"
    )


def answer(question, max_sections=5):
    """Navigate + generate a cited answer. Returns a JSON-serialisable dict."""
    sections = navigate(question, max_sections=max_sections)
    trace = [
        {"n": n, "title": s.title, "path": s.path, "source": s.source}
        for n, s in enumerate(sections, start=1)
    ]

    start = time.perf_counter()
    try:
        text, usage = _generate(_build_prompt(question, sections))
    except Exception as error:
        raise VectorlessAnswerError(f"vectorless answer generation failed: {error}") from error
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
            "sections_opened": len(trace),
            "model": MODEL,
        },
    }
