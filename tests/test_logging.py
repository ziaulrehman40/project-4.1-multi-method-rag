from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from config import middleware


def _request():
    return SimpleNamespace(
        method="GET",
        path="/conversations/7/",
        user=SimpleNamespace(is_authenticated=True, id=42),
        headers={"HX-Request": "true"},
    )


def test_request_logging_records_safe_request_metadata(monkeypatch):
    log = Mock()
    monkeypatch.setattr(middleware, "logger", log)
    response = SimpleNamespace(status_code=200)

    result = middleware.RequestLoggingMiddleware(lambda request: response)(_request())

    assert result is response
    log.debug.assert_called_once_with(
        "request.start method=%s path=%s user_id=%s htmx=%s",
        "GET",
        "/conversations/7/",
        42,
        True,
    )
    assert log.info.call_count == 1


def test_request_logging_records_unhandled_exception(monkeypatch):
    log = Mock()
    monkeypatch.setattr(middleware, "logger", log)

    def fail(request):
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        middleware.RequestLoggingMiddleware(fail)(_request())

    assert log.exception.call_count == 1
