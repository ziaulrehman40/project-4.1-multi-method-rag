"""Text embeddings for Stages 1-3, via the embedding provider adapter.

Batches to stay under the API's per-request cap; retry/backoff and the client lifecycle live
in the provider (`llm/`). Embeddings stay on Gemini (`gemini-embedding-001`, 3072-dim) because
the pgvector columns are dimension-locked. `embed_texts` / `embed_query` are the mockable seams.
"""

from llm import get_embedding_provider


EMBED_MODEL = "gemini-embedding-001"
MAX_BATCH = 32


class EmbeddingError(RuntimeError):
    """Raised when embeddings cannot be produced."""


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into 3072-dim vectors, order preserved."""
    if not texts:
        return []
    provider = get_embedding_provider()
    vectors: list[list[float]] = []
    try:
        # Send in slices of MAX_BATCH so we stay under the API's per-request batch cap.
        for start in range(0, len(texts), MAX_BATCH):
            vectors.extend(provider.embed_texts(texts[start : start + MAX_BATCH], model=EMBED_MODEL))
    except Exception as error:
        raise EmbeddingError(f"Embedding failed: {error}") from error
    return vectors


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([text])[0]
