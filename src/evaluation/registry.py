"""Unified interface over the four retrieval techniques.

Each technique's answer() returns a slightly different shape (sources / trace / …). The
adapters here normalise them all to one result dict so the query page, comparison view, and
evaluation harness can treat every technique the same:

    {technique, label, answer, evidence[], sources[], metrics, error}

- evidence : display items (label + detail + optional image) for the UI.
- sources  : ordered source identifiers (filenames), used by the eval harness for
             ranking metrics (hit@k / recall@k / MRR).
- error    : set (and the rest empty) if the technique raised — one failure never breaks
             the page or the comparison.
"""

import logging

from kg.answer import answer as _graph_answer
from multimodal.answer import answer as _multimodal_answer
from rag.answer import answer as _embedding_answer
from vectorless.answer import answer as _vectorless_answer


logger = logging.getLogger("evaluation.registry")


def _embedding(question):
    r = _embedding_answer(question)
    evidence = [
        {"label": f"{s['source']} #{s['ordinal']}", "detail": s["text"], "image_b64": ""}
        for s in r["sources"]
    ]
    return r["answer"], evidence, [s["source"] for s in r["sources"]], r["metrics"]


def _graph(question):
    r = _graph_answer(question)
    evidence = [
        {"label": f"{t['source']} · {t['section']}",
         "detail": f"({t['subject']}) {t['predicate']} ({t['object']})", "image_b64": ""}
        for t in r["trace"]
    ]
    return r["answer"], evidence, [t["source"] for t in r["trace"]], r["metrics"]


def _vectorless(question):
    r = _vectorless_answer(question)
    evidence = [{"label": t["path"], "detail": t["title"], "image_b64": ""} for t in r["trace"]]
    return r["answer"], evidence, [t["source"] for t in r["trace"]], r["metrics"]


def _multimodal(question):
    r = _multimodal_answer(question)
    evidence = [
        {"label": f"{t['kind']} p{t['page']}", "detail": t.get("context") or t["text"],
         "image_b64": t.get("image_b64", "")}
        for t in r["trace"]
    ]
    return r["answer"], evidence, [t.get("source", "") for t in r["trace"]], r["metrics"]


# Ordered: name -> (human label, adapter)
ADAPTERS = {
    "embedding": ("Embedding RAG", _embedding),
    "graph": ("Knowledge Graph", _graph),
    "vectorless": ("Vectorless", _vectorless),
    "multimodal": ("Multimodal", _multimodal),
}


def technique_choices():
    """[(name, label), ...] for dropdowns."""
    return [(name, label) for name, (label, _) in ADAPTERS.items()]


def run_technique(name, question):
    """Run one technique and return the normalised result (never raises)."""
    label, adapter = ADAPTERS[name]
    try:
        answer, evidence, sources, metrics = adapter(question)
        return {"technique": name, "label": label, "answer": answer, "evidence": evidence,
                "sources": sources, "metrics": metrics, "error": None}
    except Exception as error:  # isolate per-technique failure
        logger.warning("technique %s failed: %s", name, error)
        return {"technique": name, "label": label, "answer": "", "evidence": [],
                "sources": [], "metrics": {}, "error": str(error)}


def run_all(question):
    """Run every technique over one question (sequential). Returns a list of results."""
    return [run_technique(name, question) for name in ADAPTERS]
