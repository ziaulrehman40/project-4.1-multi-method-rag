"""Template context: the active LLM so the UI can name the model dynamically instead of
hardcoding a provider (generation is swappable via settings.LLM_GENERATION_PROVIDER)."""

from django.conf import settings

from llm import active_generation_model


def active_llm(request):
    return {
        "active_model": active_generation_model(),
        "generation_provider": settings.LLM_GENERATION_PROVIDER,
    }
