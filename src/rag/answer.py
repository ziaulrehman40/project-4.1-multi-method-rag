"""Answer generation for embedding-RAG: the 'G' in RAG.

Pipeline: hybrid retrieve -> rerank -> grounded, numbered prompt -> Gemini answer with inline
[n] citations. Returns a dict (answer, sources, reranked, metrics) that is both stored on the
chat Message (JSON) and rendered in the transparency panel.

Retrieval uses only the current question (not conversation history) — Stage 1 scope.
"""

import os
import time

from django.conf import settings
from google import genai

from .models import EMBEDDING_DIM
from .reranking import rerank
from .retrieval import hybrid_search


ANSWER_MODEL = settings.GEMINI_MODEL  # central, env-overridable
DEFAULT_POOL = 10
DEFAULT_TOP_N = 3

# Approximate published Gemini Flash rates (USD per 1M tokens). Only used to show an
# *estimated* cost in the UI; the free tier bills nothing.
INPUT_USD_PER_1M = 0.30
OUTPUT_USD_PER_1M = 2.50


class AnswerError(RuntimeError):
    """Answer generation failed at the provider boundary."""


def _generate(prompt):
    """Call Gemini once; return (text, usage-dict). Split out so tests can mock it."""
    # Strong client reference (a temporary genai.Client is GC'd mid-request).
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(model=ANSWER_MODEL, contents=prompt)
    usage = response.usage_metadata
    return (response.text or ""), {
        "input_tokens": getattr(usage, "prompt_token_count", 0) or 0,
        "output_tokens": getattr(usage, "candidates_token_count", 0) or 0,
        "total_tokens": getattr(usage, "total_token_count", 0) or 0,
    }


def _build_prompt(question, sources):
    context = "\n\n".join(f"[{s['n']}] ({s['source']}) {s['text']}" for s in sources)
    return (
        "Answer the question using ONLY the numbered context below. Cite the sources you "
        "use inline with their number, like [1] or [2]. If the answer is not in the context, "
        "say you cannot find it.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
    )


def answer(question, pool=DEFAULT_POOL, top_n=DEFAULT_TOP_N, rerank_enabled=True):
    """Retrieve, (optionally) rerank, and generate a cited answer.

    Returns a JSON-serialisable dict. `rerank_status` is one of:
    "applied" (reranked), "failed" (reranker errored → retrieval order; the non-silent
    fallback), or "off" (rerank_enabled=False → one fewer LLM call, saves quota).
    """
    candidates = hybrid_search(question, k=pool)

    if rerank_enabled:
        outcome = rerank(question, candidates, top_n=top_n)
        used = outcome.chunks
        rerank_status = "applied" if outcome.reranked else "failed"
    else:
        used = candidates[:top_n]
        rerank_status = "off"

    sources = []
    for n, chunk in enumerate(used, start=1):
        # Show whichever score the chunk carries (rerank if present, else retrieval score).
        if hasattr(chunk, "rerank_score"):
            score, method = chunk.rerank_score, "rerank"
        elif hasattr(chunk, "rrf_score"):
            score, method = chunk.rrf_score, "hybrid"
        else:
            score, method = getattr(chunk, "distance", None), "dense"
        sources.append(
            {
                "n": n,
                "source": chunk.source,
                "ordinal": chunk.ordinal,
                "text": chunk.text,
                "score": score,
                "method": method,
            }
        )

    prompt = _build_prompt(question, sources)
    start = time.perf_counter()
    try:
        text, usage = _generate(prompt)
    except Exception as error:
        raise AnswerError(f"answer generation failed: {error}") from error
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    est_cost = (
        usage["input_tokens"] / 1_000_000 * INPUT_USD_PER_1M
        + usage["output_tokens"] / 1_000_000 * OUTPUT_USD_PER_1M
    )

    return {
        "answer": text,
        "sources": sources,
        "rerank_status": rerank_status,
        "metrics": {
            **usage,
            "latency_ms": latency_ms,
            "est_cost_usd": round(est_cost, 6),
            "embedding_dim": EMBEDDING_DIM,
            "model": ANSWER_MODEL,
        },
    }
