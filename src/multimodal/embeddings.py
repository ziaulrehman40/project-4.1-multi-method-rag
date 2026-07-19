"""Multimodal embeddings (text + image) via the embedding provider adapter.

Uses gemini-embedding-2 so text and images share one 3072-dim space (cross-modal retrieval).
Kept separate from rag.embeddings, which uses the text-only gemini-embedding-001. Retry/backoff
and the client lifecycle live in the provider (`llm/`).
"""

from llm import Image, get_embedding_provider


MODEL = "gemini-embedding-2"
EMBEDDING_DIM = 3072


class MultimodalEmbeddingError(RuntimeError):
    """Embedding failed at the provider boundary."""


def embed_text(text):
    """Embed a text string into a 3072-dim vector."""
    try:
        return get_embedding_provider().embed_texts([text], model=MODEL)[0]
    except Exception as error:
        raise MultimodalEmbeddingError(f"text embedding failed: {error}") from error


def embed_image(image_bytes, mime_type="image/png"):
    """Embed raw image bytes into a 3072-dim vector (same space as text)."""
    try:
        return get_embedding_provider().embed_image(Image(data=image_bytes, mime=mime_type), model=MODEL)
    except Exception as error:
        raise MultimodalEmbeddingError(f"image embedding failed: {error}") from error
