"""Gemini provider (google-genai) — implements both generation and embedding."""

import os

from django.conf import settings
from google import genai
from google.genai import types

from .base import EmbeddingProvider, Generation, GenerationProvider, Image, with_retry


def _client():
    # Strong reference held by the caller (a temporary genai.Client is GC'd mid-request).
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _parts_to_contents(parts):
    """Map our [str | Image] parts to google-genai contents."""
    contents = []
    for part in parts:
        if isinstance(part, Image):
            contents.append(types.Part.from_bytes(data=part.data, mime_type=part.mime))
        else:
            contents.append(part)
    return contents


def _usage(response):
    u = response.usage_metadata
    return (getattr(u, "prompt_token_count", 0) or 0,
            getattr(u, "candidates_token_count", 0) or 0,
            getattr(u, "total_token_count", 0) or 0)


class GeminiGeneration(GenerationProvider):
    def __init__(self):
        self.model = settings.GEMINI_MODEL

    def _run(self, contents, json_mode, max_tokens):
        config_kwargs = {}
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"
        if max_tokens:
            config_kwargs["max_output_tokens"] = max_tokens
        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        def call():
            client = _client()
            return client.models.generate_content(model=self.model, contents=contents, config=config)

        response = with_retry(call, label=f"gemini.generate:{self.model}")
        i, o, t = _usage(response)
        return Generation(text=response.text or "", input_tokens=i, output_tokens=o, total_tokens=t)

    def generate(self, parts, *, json_mode=False, max_tokens=None):
        return self._run(_parts_to_contents(parts), json_mode, max_tokens)

    def chat(self, messages, *, json_mode=False):
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [{"text": m["content"]}]}
            for m in messages
        ]
        return self._run(contents, json_mode, None)


class GeminiEmbedding(EmbeddingProvider):
    dimensions = 3072

    def embed_texts(self, texts, *, model=None):
        model = model or "gemini-embedding-001"

        def call():
            client = _client()
            return client.models.embed_content(model=model, contents=list(texts))

        response = with_retry(call, label=f"gemini.embed:{model}")
        return [e.values for e in response.embeddings]

    def embed_image(self, image, *, model=None):
        model = model or "gemini-embedding-2"

        def call():
            client = _client()
            return client.models.embed_content(
                model=model,
                contents=[types.Part.from_bytes(data=image.data, mime_type=image.mime)],
            )

        response = with_retry(call, label=f"gemini.embed_image:{model}")
        return response.embeddings[0].values
