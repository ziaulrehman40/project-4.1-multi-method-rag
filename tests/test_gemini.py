from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from chat import gemini


def test_generate_reply_maps_history_and_calls_flash_once(monkeypatch):
    generate_content = Mock(return_value=SimpleNamespace(text="Mapped reply"))
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    client_factory = Mock(return_value=client)
    log = Mock()
    monkeypatch.setattr(gemini.genai, "Client", client_factory)
    monkeypatch.setattr(gemini, "logger", log)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    result = gemini.generate_reply(
        [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Prior answer"},
            {"role": "user", "content": "Follow-up"},
        ]
    )

    assert result == "Mapped reply"
    client_factory.assert_called_once_with(api_key="test-key")
    generate_content.assert_called_once_with(
        model=gemini.MODEL,
        contents=[
            {"role": "user", "parts": [{"text": "Question"}]},
            {"role": "model", "parts": [{"text": "Prior answer"}]},
            {"role": "user", "parts": [{"text": "Follow-up"}]},
        ],
    )
    log.debug.assert_called_once_with(
        "gemini.call.start model=%s history_messages=%d prompt_chars=%d",
        gemini.MODEL,
        3,
        29,
    )
    assert log.info.call_count == 1
    logged_values = repr(log.mock_calls)
    assert "Question" not in logged_values
    assert "Prior answer" not in logged_values
    assert "Follow-up" not in logged_values
    assert "test-key" not in logged_values


def test_generate_reply_rejects_empty_provider_response(monkeypatch):
    client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=Mock(return_value=SimpleNamespace(text=None))
        )
    )
    monkeypatch.setattr(gemini.genai, "Client", Mock(return_value=client))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with pytest.raises(gemini.GeminiError, match="empty response"):
        gemini.generate_reply([{"role": "user", "content": "Question"}])


def test_generate_reply_wraps_sdk_errors(monkeypatch):
    client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=Mock(side_effect=ConnectionError("network down"))
        )
    )
    monkeypatch.setattr(gemini.genai, "Client", Mock(return_value=client))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with pytest.raises(gemini.GeminiError, match="request failed") as error:
        gemini.generate_reply([{"role": "user", "content": "Question"}])

    assert isinstance(error.value.__cause__, ConnectionError)
