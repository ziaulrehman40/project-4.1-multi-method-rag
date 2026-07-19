"""Answer generation for vectorless (reasoning-based) RAG.

Navigate the document tree to select sections, read ONLY those sections' content, and
generate a cited answer. The `trace` is the navigation path — which sections were opened —
each identified by its breadcrumb path (the citation).
"""

import logging
import time

from llm import active_generation_model, get_generation_provider

from .navigation import navigate


logger = logging.getLogger("vectorless.answer")

# Approximate Flash rates (USD per 1M tokens); shown as an estimate only.
INPUT_USD_PER_1M = 0.30
OUTPUT_USD_PER_1M = 2.50


class VectorlessAnswerError(RuntimeError):
    """Vectorless answer generation failed at the provider boundary."""


def _generate(prompt):
    """Generate via the configured provider; return (text, usage-dict). Mockable in tests."""
    result = get_generation_provider().generate([prompt])
    return result.text, {
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "total_tokens": result.total_tokens,
    }


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
    """Navigate + generate a cited answer. Returns a JSON-serialisable dict.

    Any failure (navigation, embedding, generation) is wrapped as VectorlessAnswerError so
    callers only ever have to handle one error type.
    """
    start = time.perf_counter()
    try:
        sections = navigate(question, max_sections=max_sections)
        text, usage = _generate(_build_prompt(question, sections))
    except Exception as error:
        raise VectorlessAnswerError(f"vectorless answer failed: {error}") from error
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    trace = [
        {"n": n, "title": s.title, "path": s.path, "source": s.source}
        for n, s in enumerate(sections, start=1)
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
            "sections_opened": len(trace),
            "model": active_generation_model(),
        },
    }
