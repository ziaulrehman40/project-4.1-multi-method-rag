"""Gemini text embeddings — the only place the embedding API is called.

Kept separate from `chat.gemini` (which does generation) so retrieval can be tested
and evolved independently. Mockable in tests.

Robustness notes for the free tier:
- The BatchEmbedContents API rejects very large batches (400), so we send in small
  batches (<= MAX_BATCH).
- The free tier is rate-limited (429). google-genai fans a batch out concurrently, so a
  single 429 can close the shared client and surface as "client has been closed". We retry
  each batch with exponential backoff and a *fresh* client per attempt.
"""

import os
import time

from google import genai


EMBED_MODEL = "gemini-embedding-001"
MAX_BATCH = 32
MAX_RETRIES = 5
BASE_DELAY_SECONDS = 2.0


class EmbeddingError(RuntimeError):
    """Raised when embeddings cannot be produced after retries."""


def _client():
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _embed_batch(batch: list[str]) -> list[list[float]]:
    delay = BASE_DELAY_SECONDS
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            # Hold a strong reference to the client: `genai.Client().models...` lets the
            # Client be garbage-collected mid-request, whose __del__ closes the transport
            # and fails with "client has been closed".
            client = _client()
            response = client.models.embed_content(model=EMBED_MODEL, contents=batch)
            return [embedding.values for embedding in response.embeddings]
        except Exception as error:  # transient: rate limits, closed client, network
            last_error = error
            if attempt < MAX_RETRIES - 1:
                time.sleep(delay)
                delay *= 2
    raise EmbeddingError(f"Embedding failed after {MAX_RETRIES} attempts: {last_error}")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into 3072-dim vectors, order preserved."""
    if not texts:
        return []
    vectors: list[list[float]] = []
    # Send in slices of MAX_BATCH so we stay under the API's per-request batch cap.
    for start in range(0, len(texts), MAX_BATCH):
        vectors.extend(_embed_batch(texts[start : start + MAX_BATCH]))
    return vectors


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([text])[0]
