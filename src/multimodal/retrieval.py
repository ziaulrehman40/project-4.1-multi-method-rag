"""Cross-modal retrieval: a text question retrieves text, tables, and images together.

The question is embedded with gemini-embedding-2 (same space as the indexed content), so an
image chunk can rank against a text query. Each figure was stored as two rows (image- and
caption-embedded); we de-duplicate by `figure_key` so a figure appears at most once.
"""

from pgvector.django import CosineDistance

from .embeddings import embed_text
from .models import MultimodalChunk


DEFAULT_TOP_K = 5


def retrieve(question, k=DEFAULT_TOP_K):
    """Return the k most relevant chunks (mixed kinds), de-duplicating figures by figure_key."""
    query_vector = embed_text(question)
    # Pull a few extra so de-duplication still leaves k results.
    candidates = (
        MultimodalChunk.objects.annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[: k * 2]
    )

    results = []
    seen_figures = set()
    for chunk in candidates:
        if chunk.figure_key:
            if chunk.figure_key in seen_figures:
                continue  # same figure already included (image + caption rows)
            seen_figures.add(chunk.figure_key)
        results.append(chunk)
        if len(results) == k:
            break
    return results
