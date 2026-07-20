"""Answer generation for embedding-RAG: the 'G' in RAG.

Pipeline: hybrid retrieve -> rerank -> grounded, numbered prompt -> Gemini answer with inline
[n] citations. Returns a dict (answer, sources, reranked, metrics) that is both stored on the
chat Message (JSON) and rendered in the transparency panel.

Retrieval uses only the current question (not conversation history) — Stage 1 scope.
"""

import time

from techniques import TechniqueError, finalize_metrics, run_generation

from .models import EMBEDDING_DIM
from .reranking import rerank
from .retrieval import hybrid_search


DEFAULT_POOL = 10
DEFAULT_TOP_N = 3


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
    start = time.perf_counter()
    try:
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
            sources.append({"n": n, "source": chunk.source, "ordinal": chunk.ordinal,
                            "text": chunk.text, "score": score, "method": method})

        generation = run_generation(_build_prompt(question, sources))
    except Exception as error:
        raise TechniqueError(f"answer failed: {error}") from error

    return {
        "answer": generation.text,
        "sources": sources,
        "rerank_status": rerank_status,
        "metrics": finalize_metrics(generation, start, embedding_dim=EMBEDDING_DIM),
    }
