"""OpenAI provider — generation only (chat completions, incl. vision + JSON).

Paid tier: generous limits, so all figures fit (max_images high) and JSON mode is reliable.
Embeddings stay on Gemini (dimension-locked). Model defaults to a small, cheap model.
"""

import base64
import os

from django.conf import settings

from .base import Generation, GenerationProvider, Image, with_retry


def _client():
    from openai import OpenAI  # lazy import so the app runs without openai unless selected

    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


class OpenAIGeneration(GenerationProvider):
    max_images = 6  # paid tier has generous token limits

    def __init__(self):
        self.model = settings.OPENAI_MODEL

    def _complete(self, messages, *, json_mode=False, max_tokens=None):
        # Note: we do NOT set response_format={"type":"json_object"} — it forces a top-level
        # OBJECT, but several callers ask for a JSON ARRAY (triples, rerank scores, nav
        # indices). The prompt already specifies the exact JSON shape and generate_json parses
        # it leniently, so the model returns arrays or objects as asked.
        # Guardrail: always bound output. Callers may raise it (e.g. vision); otherwise the
        # global default keeps a single request from running up an unbounded token bill.
        kwargs = {"model": self.model, "messages": messages,
                  "max_tokens": max_tokens or settings.GENERATION_MAX_TOKENS}
        response = with_retry(lambda: _client().chat.completions.create(**kwargs),
                              label=f"openai:{self.model}")
        usage = response.usage
        return Generation(
            text=response.choices[0].message.content or "",
            input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )

    def generate(self, parts, *, json_mode=False, max_tokens=None):
        images = [p for p in parts if isinstance(p, Image)]
        text = "\n".join(p for p in parts if isinstance(p, str))
        if images:
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
