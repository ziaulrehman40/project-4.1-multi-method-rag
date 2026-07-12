import logging
import os
import time

from django.conf import settings
from google import genai


logger = logging.getLogger(__name__)

# Model is configured centrally (settings.GEMINI_MODEL, env-overridable).
MODEL = settings.GEMINI_MODEL


class GeminiError(RuntimeError):
    """A reply could not be generated at the provider boundary."""


def generate_reply(history: list[dict]) -> str:
    """Generate one plain Gemini reply from persisted conversation history.

    Stage 0 deliberately performs no retrieval, embedding, or document lookup.
    """
    prompt_chars = sum(len(item["content"]) for item in history)
    logger.debug(
        "gemini.call.start model=%s history_messages=%d prompt_chars=%d",
        MODEL,
        len(history),
        prompt_chars,
    )
    contents = [
        {
            "role": "model" if item["role"] == "assistant" else "user",
            "parts": [{"text": item["content"]}],
        }
        for item in history
    ]
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    started_at = time.perf_counter()
    try:
        response = client.models.generate_content(model=MODEL, contents=contents)
    except Exception as error:
        logger.exception(
            "gemini.call.error model=%s history_messages=%d prompt_chars=%d elapsed_ms=%.1f",
            MODEL,
            len(history),
            prompt_chars,
            (time.perf_counter() - started_at) * 1000,
        )
        raise GeminiError("Gemini request failed.") from error
    if not response.text:
        logger.error(
            "gemini.call.empty model=%s history_messages=%d elapsed_ms=%.1f",
            MODEL,
            len(history),
            (time.perf_counter() - started_at) * 1000,
        )
        raise GeminiError("Gemini returned an empty response.")
    logger.info(
        "gemini.call.complete model=%s history_messages=%d prompt_chars=%d response_chars=%d elapsed_ms=%.1f",
        MODEL,
        len(history),
        prompt_chars,
        len(response.text),
        (time.perf_counter() - started_at) * 1000,
    )
    return response.text
