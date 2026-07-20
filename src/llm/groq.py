"""Groq provider — generation only (OpenAI-compatible chat completions).

Uses ONE model (settings.GROQ_MODEL) for text, JSON, and vision so a provider-wide comparison
is fair (same model across every technique). The default model is a reasoning model that emits
<think>…</think>; we ask Groq to hide it (reasoning_format="hidden") and strip any that leaks.
Embeddings are not provided here — they stay on Gemini (dimension-locked).
"""

import base64
import os
import re

from django.conf import settings

from .base import Generation, GenerationProvider, Image, with_retry


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def _client():
    from groq import Groq  # lazy import so the app runs without groq unless it's selected

    return Groq(api_key=os.environ["GROQ_API_KEY"])


def _strip_reasoning(text):
    return _THINK.sub("", text or "").strip()


class GroqGeneration(GenerationProvider):
    max_images = 1  # free-tier 8000 TPM: two readable charts already exceed it
    # Approximate qwen (Groq) rates (USD per 1M tokens); indicative only.
    input_usd_per_1m = 0.29
    output_usd_per_1m = 0.59

    def __init__(self):
        self.model = settings.GROQ_MODEL

    def _complete(self, messages, *, json_mode=False, max_tokens=None):
        # Reasoning model quirks with Groq:
        # - response_format=json_object 400s (json_validate_failed) on larger outputs.
        # - reasoning_format="hidden" can return EMPTY content on larger outputs.
        # So we let reasoning come back inline as <think>…</think>, strip it ourselves, and
        # let generate_json parse the remainder leniently. Callers already ask for JSON.
        # max_completion_tokens counts toward the per-minute token limit (free tier: 8000 TPM),
        # so image requests pass a smaller budget to leave room for the image's input tokens.
        kwargs = {"model": self.model, "messages": messages,
                  "max_completion_tokens": max_tokens or settings.GROQ_MAX_TOKENS}
        response = with_retry(lambda: _client().chat.completions.create(**kwargs),
                              label=f"groq:{self.model}")
        usage = response.usage
        return Generation(
            text=_strip_reasoning(response.choices[0].message.content),
            input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )

    def generate(self, parts, *, json_mode=False, max_tokens=None):
        images = [p for p in parts if isinstance(p, Image)]
        text = "\n".join(p for p in parts if isinstance(p, str))
        if images:
            # OpenAI-style multimodal content: text + image_url data URIs.
            content = [{"type": "text", "text": text}]
            for image in images:
                b64 = base64.b64encode(image.data).decode("ascii")
                content.append({"type": "image_url",
                                "image_url": {"url": f"data:{image.mime};base64,{b64}"}})
            return self._complete([{"role": "user", "content": content}], max_tokens=max_tokens)
        return self._complete([{"role": "user", "content": text}],
                              json_mode=json_mode, max_tokens=max_tokens)

    def chat(self, messages, *, json_mode=False):
        mapped = [{"role": m["role"], "content": m["content"]} for m in messages]
        return self._complete(mapped, json_mode=json_mode)
