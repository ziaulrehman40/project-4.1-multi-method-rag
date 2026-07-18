"""Multimodal embeddings via gemini-embedding-2.

Unlike Stage 1's text-only gemini-embedding-001, this model embeds BOTH text and images
into the same 3072-dim space — so a text question can retrieve a relevant chart image
(cross-modal). We keep this separate from rag.embeddings because it uses a different model
and accepts image bytes.
"""

import logging
import os
import time

from google import genai
from google.genai import types


logger = logging.getLogger("multimodal.embed")

MODEL = "gemini-embedding-2"
EMBEDDING_DIM = 3072
MAX_RETRIES = 4
BASE_DELAY_SECONDS = 2.0


class MultimodalEmbeddingError(RuntimeError):
    """Embedding failed at the provider boundary after retries."""


def _embed(contents):
    """Embed a single `contents` payload (text string or image Part); retry transient errors."""
    delay = BASE_DELAY_SECONDS
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            # Strong client reference (a temporary genai.Client is GC'd mid-request).
            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            response = client.models.embed_content(model=MODEL, contents=contents)
            return response.embeddings[0].values
        except Exception as error:
            last_error = error
            if attempt < MAX_RETRIES - 1:
                logger.warning("multimodal.embed.retry attempt=%d error=%s", attempt + 1, error)
                time.sleep(delay)
                delay *= 2
    raise MultimodalEmbeddingError(f"embedding failed after {MAX_RETRIES} attempts: {last_error}")


def embed_text(text):
    """Embed a text string into a 3072-dim vector."""
    return _embed([text])


def embed_image(image_bytes, mime_type="image/png"):
    """Embed raw image bytes into a 3072-dim vector (same space as text)."""
    return _embed([types.Part.from_bytes(data=image_bytes, mime_type=mime_type)])
