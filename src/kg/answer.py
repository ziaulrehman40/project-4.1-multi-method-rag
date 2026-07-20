"""Answer generation for knowledge-graph RAG.

Retrieve a subgraph (kg.retrieval.graph_search), present its edges as numbered facts with
provenance, and have Gemini compose a cited answer. Returns the answer plus a `trace` — the
exact edges (nodes + relationship + source/section) used — which is graph RAG's auditability
win over vector RAG (you see the reasoning path, not just "nearby chunks").
"""

import logging
import time

from techniques import TechniqueError, finalize_metrics, run_generation

from .retrieval import graph_search


logger = logging.getLogger("kg.answer")


def _build_prompt(question, trace):
    facts = "\n".join(
        f"[{t['n']}] ({t['subject']}) {t['predicate']} ({t['object']})"
        f"  — {t['source']}, {t['section']}"
        for t in trace
    )
    return (
        "Answer the question using ONLY the numbered facts from the knowledge graph below. "
        "Cite the facts you use inline with their number, like [1]. If the facts do not "
        "answer the question, say you cannot find it.\n\n"
        f"Facts:\n{facts}\n\nQuestion: {question}\nAnswer:"
    )


def answer(question, seeds=5, hops=1, max_edges=20):
    """Retrieve a subgraph and generate a cited answer. Returns a JSON-serialisable dict.

    Any failure (embedding, generation) is wrapped as GraphAnswerError.
    """
    start = time.perf_counter()
    try:
        edges = graph_search(question, seeds=seeds, hops=hops, max_edges=max_edges)
        trace = [
            {
                "n": n,
                "subject": edge.subject.name,
                "predicate": edge.predicate,
                "object": edge.object.name,
                "source": edge.source,
                "section": edge.section,
            }
            for n, edge in enumerate(edges, start=1)
        ]
        generation = run_generation(_build_prompt(question, trace))
    except Exception as error:
        raise TechniqueError(f"graph answer failed: {error}") from error

    return {
        "answer": generation.text,
        "trace": trace,
        "metrics": finalize_metrics(generation, start, edges_used=len(trace)),
    }
