from unittest.mock import Mock

import pytest

from chat import assistant
from llm import Generation


def _provider(generation=None, error=None):
    provider = Mock()
    if error is not None:
        provider.chat.side_effect = error
    else:
        provider.chat.return_value = generation
    return provider


def test_generate_reply_returns_provider_text(monkeypatch):
    provider = _provider(Generation(text="Mapped reply", total_tokens=10))
    monkeypatch.setattr(assistant, "get_generation_provider", lambda: provider)

    history = [{"role": "user", "content": "Question"}, {"role": "assistant", "content": "Prior"}]
    assert assistant.generate_reply(history) == "Mapped reply"
    provider.chat.assert_called_once_with(history)


def test_generate_reply_rejects_empty_response(monkeypatch):
    monkeypatch.setattr(assistant, "get_generation_provider", lambda: _provider(Generation(text="")))
    with pytest.raises(assistant.AssistantError):
        assistant.generate_reply([{"role": "user", "content": "Q"}])


def test_generate_reply_wraps_provider_errors(monkeypatch):
    monkeypatch.setattr(assistant, "get_generation_provider",
                        lambda: _provider(error=RuntimeError("boom")))
    with pytest.raises(assistant.AssistantError):
        assistant.generate_reply([{"role": "user", "content": "Q"}])
