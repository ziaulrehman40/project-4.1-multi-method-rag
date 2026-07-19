"""Reranking: a second, more precise pass over retrieved candidates.

Retrieval (bi-encoder embeddings + keyword) is fast but coarse. A reranker looks at the
query and each candidate *together* and scores true relevance. We use an LLM-as-reranker
(Gemini) rather than a dedicated cross-encoder model: no new infrastructure, works on the
free tier and on Render, and one call scores the whole candidate pool.

Fallback is never silent: if the rerank call fails, we log a warning and return the original
retrieval order with `reranked=False` so callers (and the UI) can flag it.
"""

import logging
from dataclasses import dataclass

from llm import get_generation_provider


logger = logging.getLogger("rag.rerank")

DEFAULT_TOP_N = 3


@dataclass
class RerankOutcome:
    """Result of a rerank attempt.

    `reranked` is False when we fell back to retrieval order (with `note` explaining why),
    so a caller can surface a warning instead of failing silently.
    """

    chunks: list
    reranked: bool
    note: str | None = None


def _score_with_gemini(query, chunks):
    """Ask the LLM for a 0-10 relevance score per candidate; returns a list aligned to chunks.

    (Name kept for continuity; uses the configured generation provider.)
    """
    listing = "\n".join(f"[{i}] {chunk.text}" for i, chunk in enumerate(chunks))
    prompt = (
        "Rate how well each candidate passage answers the question, from 0 (irrelevant) "
        "to 10 (directly answers it).\n\n"
        f"Question: {query}\n\nCandidates:\n{listing}\n\n"
        'Return ONLY a JSON array with one object per candidate: '
        '[{"index": 0, "score": 7}, ...]'
    )
    data, _ = get_generation_provider().generate_json([prompt])

    scores = [0.0] * len(chunks)
    for item in data:
        index = item["index"]
        if 0 <= index < len(chunks):  # ignore any out-of-range indices the model invents
            scores[index] = float(item["score"])
    return scores


def rerank(query, chunks, top_n=DEFAULT_TOP_N):
    """Reorder `chunks` by LLM-judged relevance and keep the best `top_n`.

    On success each returned chunk carries `.rerank_score`. On failure returns the first
    `top_n` in the original order with `reranked=False` (and logs a warning) — never silent.
    """
    if not chunks:
        return RerankOutcome(chunks=[], reranked=True)

    try:
        scores = _score_with_gemini(query, chunks)
    except Exception as error:
        logger.warning(
            "rerank.fallback: reranking failed (%s); returning retrieval order", error
        )
        return RerankOutcome(chunks=list(chunks[:top_n]), reranked=False, note=str(error))

    ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)
    top = []
    for chunk, score in ranked[:top_n]:
        chunk.rerank_score = score
        top.append(chunk)
    return RerankOutcome(chunks=top, reranked=True)
