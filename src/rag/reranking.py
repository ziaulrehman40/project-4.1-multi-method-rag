"""Reranking: a second, more precise pass over retrieved candidates.

Retrieval (bi-encoder embeddings + keyword) is fast but coarse. A reranker looks at the
query and each candidate *together* and scores true relevance. We use an LLM-as-reranker
(Gemini) rather than a dedicated cross-encoder model: no new infrastructure, works on the
free tier and on Render, and one call scores the whole candidate pool.

Fallback is never silent: if the rerank call fails, we log a warning and return the original
retrieval order with `reranked=False` so callers (and the UI) can flag it.
"""

import json
import logging
import os
from dataclasses import dataclass

from django.conf import settings
from google import genai
from google.genai import types


logger = logging.getLogger("rag.rerank")

RERANK_MODEL = settings.GEMINI_MODEL  # central, env-overridable
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
    """Ask Gemini for a 0-10 relevance score per candidate; returns a list aligned to chunks."""
    # Hold a strong client reference (a temporary genai.Client is GC'd mid-request).
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    listing = "\n".join(f"[{i}] {chunk.text}" for i, chunk in enumerate(chunks))
    prompt = (
        "Rate how well each candidate passage answers the question, from 0 (irrelevant) "
        "to 10 (directly answers it).\n\n"
        f"Question: {query}\n\nCandidates:\n{listing}\n\n"
        'Return ONLY a JSON array with one object per candidate: '
        '[{"index": 0, "score": 7}, ...]'
    )
    response = client.models.generate_content(
        model=RERANK_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    scores = [0.0] * len(chunks)
    for item in json.loads(response.text):
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
