from types import SimpleNamespace

import pytest

from llm import Image, get_generation_provider
from llm import base as base_mod
from llm import gemini as gemini_mod
from llm import groq as groq_mod
from llm.base import with_retry


# --------------------------------------------------------------------------- retry

class _HTTPError(RuntimeError):
    """Stand-in for a provider SDK error carrying an HTTP status."""

    def __init__(self, status):
        super().__init__(f"http {status}")
        self.status_code = status


def test_with_retry_succeeds_after_transient_failure(monkeypatch):
    monkeypatch.setattr(base_mod.time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise _HTTPError(429)  # rate limit — transient, should retry
        return "ok"

    assert with_retry(flaky, label="t") == "ok"
    assert calls["n"] == 2


def test_with_retry_gives_up_on_transient(monkeypatch):
    monkeypatch.setattr(base_mod.time, "sleep", lambda _s: None)
    with pytest.raises(_HTTPError):
        with_retry(lambda: (_ for _ in ()).throw(_HTTPError(503)), label="t")


def test_with_retry_does_not_retry_hard_errors(monkeypatch):
    """A 400/401 is a caller/permission error: raise immediately, don't hammer the API."""
    monkeypatch.setattr(base_mod.time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def bad_request():
        calls["n"] += 1
        raise _HTTPError(400)

    with pytest.raises(_HTTPError):
        with_retry(bad_request, label="t")
    assert calls["n"] == 1  # no retries


# -------------------------------------------------------------------------- gemini

def test_gemini_generate_maps_parts_and_usage(monkeypatch):
    def fake_client(api_key):
        def generate_content(model, contents, config):
            return SimpleNamespace(text="hi", usage_metadata=SimpleNamespace(
                prompt_token_count=3, candidates_token_count=1, total_token_count=4))
        return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    monkeypatch.setattr(gemini_mod.genai, "Client", fake_client)
    monkeypatch.setenv("GEMINI_API_KEY", "k")

    result = gemini_mod.GeminiGeneration().generate(["hello"])
    assert result.text == "hi" and result.total_tokens == 4


# ---------------------------------------------------------------------------- groq

def test_groq_strips_reasoning_and_routes_vision(monkeypatch):
    captured = {}

    class FakeGroq:
        def __init__(self):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

        def _create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="<think>x</think>OK"))],
                usage=SimpleNamespace(prompt_tokens=2, completion_tokens=1, total_tokens=3))

    monkeypatch.setattr(groq_mod, "_client", lambda: FakeGroq())
    provider = groq_mod.GroqGeneration()

    text_result = provider.generate(["hi"])
    assert text_result.text == "OK"  # <think>…</think> stripped

    provider.generate(["describe", Image(data=b"png")])
    content = captured["messages"][0]["content"]
    assert isinstance(content, list) and any(c.get("type") == "image_url" for c in content)


# -------------------------------------------------------------------------- openai

def test_openai_generate_text_and_vision(monkeypatch):
    from llm import openai as openai_mod

    captured = {}

    class FakeOpenAI:
        def __init__(self):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

        def _create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Phishing"))],
                usage=SimpleNamespace(prompt_tokens=5, completion_tokens=1, total_tokens=6))

    monkeypatch.setattr(openai_mod, "_client", lambda: FakeOpenAI())
    provider = openai_mod.OpenAIGeneration()

    assert provider.generate(["hi"]).text == "Phishing"
    provider.generate(["describe", Image(data=b"png")])
    content = captured["messages"][0]["content"]
    assert any(c.get("type") == "image_url" for c in content)


# ------------------------------------------------------------------------- factory

def test_factory_selects_provider_by_name():
    from llm.gemini import GeminiGeneration
    from llm.groq import GroqGeneration
    from llm.openai import OpenAIGeneration

    assert isinstance(get_generation_provider("gemini"), GeminiGeneration)
    assert isinstance(get_generation_provider("groq"), GroqGeneration)
    assert isinstance(get_generation_provider("openai"), OpenAIGeneration)
    with pytest.raises(ValueError):
        get_generation_provider("nope")
