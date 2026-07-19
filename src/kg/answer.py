"""Answer generation for knowledge-graph RAG.

Retrieve a subgraph (kg.retrieval.graph_search), present its edges as numbered facts with
provenance, and have Gemini compose a cited answer. Returns the answer plus a `trace` — the
exact edges (nodes + relationship + source/section) used — which is graph RAG's auditability
win over vector RAG (you see the reasoning path, not just "nearby chunks").
"""

import logging
import time

from llm import active_generation_model, get_generation_provider

from .retrieval import graph_search


logger = logging.getLogger("kg.answer")

# Approximate Flash rates (USD per 1M tokens); shown as an *estimate* only.
INPUT_USD_PER_1M = 0.30
OUTPUT_USD_PER_1M = 2.50


class GraphAnswerError(RuntimeError):
    """Graph answer generation failed at the provider boundary."""


def _generate(prompt):
    """Generate via the configured provider; return (text, usage-dict). Mockable in tests."""
    result = get_generation_provider().generate([prompt])
    return result.text, {
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "total_tokens": result.total_tokens,
    }


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
        text, usage = _generate(_build_prompt(question, trace))
    except Exception as error:
        raise GraphAnswerError(f"graph answer failed: {error}") from error
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
            "edges_used": len(trace),
            "model": active_generation_model(),
        },
    }
