"""Answer generation for knowledge-graph RAG.

Retrieve a subgraph (kg.retrieval.graph_search), present its edges as numbered facts with
provenance, and have Gemini compose a cited answer. Returns the answer plus a `trace` — the
exact edges (nodes + relationship + source/section) used — which is graph RAG's auditability
win over vector RAG (you see the reasoning path, not just "nearby chunks").
"""

import logging
import os
import time

from django.conf import settings
from google import genai

from .retrieval import graph_search


logger = logging.getLogger("kg.answer")

MODEL = settings.GEMINI_MODEL
MAX_RETRIES = 4
BASE_DELAY_SECONDS = 2.0

# Approximate Gemini Flash rates (USD per 1M tokens); shown as an *estimate* only.
INPUT_USD_PER_1M = 0.30
OUTPUT_USD_PER_1M = 2.50


class GraphAnswerError(RuntimeError):
    """Graph answer generation failed at the provider boundary."""


def _generate(prompt):
    """One Gemini call, retrying transient 503/429 with backoff. Returns (text, usage)."""
    delay = BASE_DELAY_SECONDS
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            # Strong client reference (a temporary genai.Client is GC'd mid-request).
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
                logger.warning("kg.answer.retry attempt=%d error=%s", attempt + 1, error)
                time.sleep(delay)
                delay *= 2
    raise last_error


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
    """Retrieve a subgraph and generate a cited answer. Returns a JSON-serialisable dict."""
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

    start = time.perf_counter()
    try:
        text, usage = _generate(_build_prompt(question, trace))
    except Exception as error:
        raise GraphAnswerError(f"graph answer generation failed: {error}") from error
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
            "model": MODEL,
        },
    }
