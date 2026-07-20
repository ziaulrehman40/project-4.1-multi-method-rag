"""Answer generation for vectorless (reasoning-based) RAG.

Navigate the document tree to select sections, read ONLY those sections' content, and
generate a cited answer. The `trace` is the navigation path — which sections were opened —
each identified by its breadcrumb path (the citation).
"""

import logging
import time

from techniques import TechniqueError, finalize_metrics, run_generation

from .navigation import navigate


logger = logging.getLogger("vectorless.answer")


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
        generation = run_generation(_build_prompt(question, sections))
    except Exception as error:
        raise TechniqueError(f"vectorless answer failed: {error}") from error

    trace = [
        {"n": n, "title": s.title, "path": s.path, "source": s.source}
        for n, s in enumerate(sections, start=1)
    ]
    return {
        "answer": generation.text,
        "trace": trace,
        "metrics": finalize_metrics(generation, start, sections_opened=len(trace)),
    }
