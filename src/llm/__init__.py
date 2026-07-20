"""LLM provider factory. Swap providers via settings — no code changes elsewhere.

    settings.LLM_GENERATION_PROVIDER   # "gemini" (default) | "groq"
    settings.LLM_EMBEDDING_PROVIDER    # "gemini" (default) — dimension-locked to 3072
"""

from functools import lru_cache

from django.conf import settings

from .base import EmbeddingProvider, Generation, GenerationProvider, Image


@lru_cache(maxsize=None)
def get_generation_provider(name=None):
    name = name or settings.LLM_GENERATION_PROVIDER
    if name == "gemini":
        from .gemini import GeminiGeneration
        return GeminiGeneration()
    if name == "groq":
        from .groq import GroqGeneration
        return GroqGeneration()
    if name == "openai":
        from .openai import OpenAIGeneration
        return OpenAIGeneration()
    raise ValueError(f"unknown generation provider: {name!r}")


def active_generation_model():
    """The model id of the active generation provider (for metrics/labels)."""
    return get_generation_provider().model


@lru_cache(maxsize=None)
def get_embedding_provider(name=None):
    name = name or settings.LLM_EMBEDDING_PROVIDER
    if name == "gemini":
        from .gemini import GeminiEmbedding
        return GeminiEmbedding()
    raise ValueError(f"unknown embedding provider: {name!r}")


__all__ = ["get_generation_provider", "get_embedding_provider",
           "GenerationProvider", "EmbeddingProvider", "Generation", "Image"]
