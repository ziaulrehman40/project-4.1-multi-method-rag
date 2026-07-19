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
    """Run `call()`, retrying transient provider errors (503/429/network) with backoff."""
    delay = BASE_DELAY_SECONDS
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return call()
        except Exception as error:
            last_error = error
            if attempt < MAX_RETRIES - 1:
                logger.warning("llm.retry label=%s attempt=%d error=%s", label, attempt + 1, error)
                time.sleep(delay)
                delay *= 2
    raise last_error


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
