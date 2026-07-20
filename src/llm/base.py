"""Provider-agnostic LLM interfaces + shared retry.

All LLM SDK usage lives under the `llm` package. The rest of the app depends only on these
interfaces, so a provider is swapped via settings (LLM_GENERATION_PROVIDER) with no code
changes. Retry/backoff and usage extraction are centralised here instead of being copy-pasted
across every technique.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from llm_json import loads_lenient


logger = logging.getLogger("llm")

MAX_RETRIES = 4
BASE_DELAY_SECONDS = 2.0

# HTTP statuses worth retrying: rate limits, request timeouts, and server-side blips. A hard
# 4xx (400 bad request, 401 auth, 403, 404) is a caller/permission error — retrying it just
# hammers the API and wastes backoff, so we fail fast on those.
TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


def _is_transient(error):
    """True if `error` looks retryable (rate limit / server / network), False for hard errors.

    Provider SDKs (openai, groq, google-genai) expose the HTTP status differently, so we probe
    the common attributes. With no HTTP status it's a network/timeout-class error — retry those;
    an unclassifiable exception (e.g. a logic bug) is NOT retried."""
    status = (getattr(error, "status_code", None)
              or getattr(error, "code", None)
              or getattr(getattr(error, "response", None), "status_code", None))
    if isinstance(status, int):
        return status in TRANSIENT_STATUS
    name = type(error).__name__.lower()
    return any(k in name for k in ("timeout", "connection", "apiconnection"))


@dataclass
class Image:
    """An image part for multimodal prompts / embeddings."""

    data: bytes
    mime: str = "image/png"


@dataclass
class Generation:
    """A generation result with token usage (0s if the provider doesn't report them)."""

    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


def with_retry(call, *, label):
    """Run `call()`, retrying only transient provider errors (429/5xx/network) with backoff.

    Hard errors (400/401/403/404) are raised immediately — retrying them wastes time and calls."""
    delay = BASE_DELAY_SECONDS
    for attempt in range(MAX_RETRIES):
        try:
            return call()
        except Exception as error:
            if not _is_transient(error) or attempt == MAX_RETRIES - 1:
                raise
            logger.warning("llm.retry label=%s attempt=%d error=%s", label, attempt + 1, error)
            time.sleep(delay)
            delay *= 2


class GenerationProvider(ABC):
    """Text/vision generation. `parts` is a single-turn prompt: a list of str and/or Image."""

    # How many images a single request can afford (per-minute token limits). Providers with
    # tight free-tier caps (e.g. Groq's 8000 TPM) override this lower.
    max_images = 6

    @abstractmethod
    def generate(self, parts, *, json_mode=False, max_tokens=None) -> Generation: ...

    @abstractmethod
    def chat(self, messages, *, json_mode=False) -> Generation:
        """Multi-turn: messages = [{'role': 'user'|'assistant', 'content': str}]."""

    def generate_json(self, parts, *, max_tokens=None):
        """Generate with JSON mode and parse leniently. Returns (parsed, Generation)."""
        result = self.generate(parts, json_mode=True, max_tokens=max_tokens)
        return loads_lenient(result.text), result


class EmbeddingProvider(ABC):
    """Text + image embeddings into a fixed-dimensional space."""

    dimensions: int

    @abstractmethod
    def embed_texts(self, texts, *, model=None) -> list: ...

    @abstractmethod
    def embed_image(self, image: Image, *, model=None) -> list: ...
