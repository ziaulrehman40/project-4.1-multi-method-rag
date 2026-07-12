"""Vector retrieval: embed the query, then find the nearest chunks by cosine distance.

This is the pgvector replacement for the hand-rolled cosine loop from the early spike:
`CosineDistance` runs the nearest-neighbour search inside Postgres.
"""

from pgvector.django import CosineDistance

from .embeddings import embed_query
from .models import DocumentChunk


DEFAULT_TOP_K = 5


def retrieve(question: str, k: int = DEFAULT_TOP_K):
    """Return the k chunks most similar to the question, nearest first.

    Each result carries a `.distance` (cosine distance, 0 = identical) so callers can
    inspect and threshold scores for transparency.
    """
    query_vector = embed_query(question)
    return list(
        DocumentChunk.objects.annotate(
            distance=CosineDistance("embedding", query_vector)
        ).order_by("distance")[:k]
    )
