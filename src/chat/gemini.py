"""Plain chat generation (Stage 0) — now via the provider adapter.

Retrieval-free: one generation call over the conversation history through whichever provider
is configured (settings.LLM_GENERATION_PROVIDER). Named `gemini` for historical continuity.
"""

import logging

from llm import get_generation_provider


logger = logging.getLogger(__name__)


class GeminiError(RuntimeError):
    """A reply could not be generated at the provider boundary."""


def generate_reply(history: list[dict]) -> str:
    """Generate one plain reply from persisted conversation history ([{role, content}, ...])."""
    logger.debug("chat.generate.start history_messages=%d", len(history))
    try:
        result = get_generation_provider().chat(history)
    except Exception as error:
        logger.exception("chat.generate.error history_messages=%d", len(history))
        raise GeminiError("Generation request failed.") from error
    if not result.text:
        raise GeminiError("The model returned an empty response.")
    logger.info("chat.generate.complete history_messages=%d tokens=%d",
                len(history), result.total_tokens)
    return result.text
