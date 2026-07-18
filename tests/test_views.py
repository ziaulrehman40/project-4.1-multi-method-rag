from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from chat import gemini
from chat.models import Conversation, Message


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("method", "url_name", "args", "data"),
    [
        ("get", "conversation-list", [], None),
        ("post", "conversation-create", [], None),
        ("get", "conversation-detail", [1], None),
        ("post", "message-create", [1], {"content": "Private"}),
        ("post", "conversation-rename", [1], {"title": "Private"}),
        ("post", "conversation-delete", [1], None),
    ],
)
def test_login_required_redirects(client, method, url_name, args, data):
    client.logout()

    url = reverse(url_name, args=args)
    response = getattr(client, method)(url, data=data)

    assert response.status_code == 302
    assert response.url == f'{reverse("login")}?next={url}'


def test_create_conversation(client, user):
    response = client.post(reverse("conversation-create"))

    conversation = Conversation.objects.get()
    assert conversation.owner == user
    assert response.status_code == 302
    assert response.url == reverse("conversation-detail", args=[conversation.id])


def test_load_history(client, user):
    conversation = Conversation.objects.create(owner=user)
    Message.objects.create(
        conversation=conversation,
        role="user",
        content="Explain SOC 2 controls.",
    )
    Message.objects.create(
        conversation=conversation,
        role="assistant",
        content="SOC 2 controls support trust service criteria.",
    )

    response = client.get(reverse("conversation-detail", args=[conversation.id]))

    assert response.status_code == 200
    assert response.content.count(b"Explain SOC 2 controls.") == 1
    assert response.content.count(b"SOC 2 controls support trust service criteria.") == 1


def test_detail_configures_htmx_to_render_provider_errors(client, user):
    conversation = Conversation.objects.create(owner=user)

    response = client.get(reverse("conversation-detail", args=[conversation.id]))

    assert b"htmx:beforeSwap" in response.content
    assert b"shouldSwap = true" in response.content


def test_post_message_saves_user_and_assistant(client, user, monkeypatch):
    conversation = Conversation.objects.create(owner=user)
    generate_reply = Mock(return_value="A fixed Gemini reply.")
    monkeypatch.setattr("chat.gemini.generate_reply", generate_reply)

    response = client.post(
        reverse("message-create", args=[conversation.id]),
        {"content": "What does GDPR require?"},
    )

    messages = list(conversation.messages.values("role", "content"))
    assert messages == [
        {"role": "user", "content": "What does GDPR require?"},
        {"role": "assistant", "content": "A fixed Gemini reply."},
    ]
    generate_reply.assert_called_once_with(
        [{"role": "user", "content": "What does GDPR require?"}]
    )
    assert response.status_code == 302
    assert response.url == reverse("conversation-detail", args=[conversation.id])


def test_post_message_sends_full_history(client, user, monkeypatch):
    conversation = Conversation.objects.create(owner=user)
    Message.objects.create(conversation=conversation, role="user", content="First question")
    Message.objects.create(
        conversation=conversation,
        role="assistant",
        content="First answer",
    )
    generate_reply = Mock(return_value="Second answer")
    monkeypatch.setattr("chat.gemini.generate_reply", generate_reply)

    client.post(
        reverse("message-create", args=[conversation.id]),
        {"content": "Second question"},
    )

    generate_reply.assert_called_once_with(
        [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
        ]
    )


def test_htmx_post_returns_both_messages(client, user, monkeypatch):
    conversation = Conversation.objects.create(owner=user)
    monkeypatch.setattr("chat.gemini.generate_reply", Mock(return_value="HTMX answer"))

    response = client.post(
        reverse("message-create", args=[conversation.id]),
        {"content": "HTMX question"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert b"HTMX question" in response.content
    assert b"HTMX answer" in response.content
    assert b"<html" not in response.content


def test_blank_message_is_rejected_without_llm_call(client, user, monkeypatch):
    conversation = Conversation.objects.create(owner=user)
    generate_reply = Mock()
    monkeypatch.setattr("chat.gemini.generate_reply", generate_reply)

    response = client.post(
        reverse("message-create", args=[conversation.id]),
        {"content": "   "},
    )

    assert response.status_code == 400
    assert Message.objects.count() == 0
    generate_reply.assert_not_called()


def test_llm_failure_does_not_leave_half_saved_turn(client, user, monkeypatch):
    conversation = Conversation.objects.create(owner=user)
    monkeypatch.setattr(
        "chat.gemini.generate_reply",
        Mock(side_effect=gemini.GeminiError("provider unavailable")),
    )

    response = client.post(
        reverse("message-create", args=[conversation.id]),
        {"content": "Will this persist?"},
    )

    assert response.status_code == 502
    assert b"could not get a reply" in response.content.lower()
    assert Message.objects.count() == 0


def test_embedding_technique_uses_rag_and_stores_metadata(client, user, monkeypatch):
    conversation = Conversation.objects.create(owner=user)
    fake_result = {
        "answer": "Report within 72 hours [1].",
        "sources": [{"n": 1, "source": "gdpr.md", "ordinal": 4, "text": "…", "score": 9.0, "method": "rerank"}],
        "rerank_status": "applied",
        "metrics": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120,
                    "latency_ms": 12.3, "est_cost_usd": 0.0, "embedding_dim": 3072, "model": "gemini-2.5-flash-lite"},
    }
    captured = {}

    def fake_answer(question, rerank_enabled=True):
        captured["question"] = question
        captured["rerank_enabled"] = rerank_enabled
        return fake_result

    monkeypatch.setattr("chat.views.generate_rag_answer", fake_answer)

    response = client.post(
        reverse("message-create", args=[conversation.id]),
        {"content": "How fast must a breach be reported?", "technique": "embedding", "rerank": "on"},
    )

    assert response.status_code == 302
    assistant = conversation.messages.get(role="assistant")
    assert assistant.technique == "embedding"
    assert assistant.content == "Report within 72 hours [1]."
    assert assistant.metadata["sources"][0]["source"] == "gdpr.md"
    assert assistant.metadata["rerank_status"] == "applied"
    # Retrieval uses the latest question only (Stage 1 scope); rerank checkbox honored.
    assert captured["question"] == "How fast must a breach be reported?"
    assert captured["rerank_enabled"] is True


def test_graph_technique_routes_to_kg_and_stores_trace(client, user, monkeypatch):
    conversation = Conversation.objects.create(owner=user)
    fake_result = {
        "answer": "Reported to the authority [1].",
        "trace": [{"n": 1, "subject": "breach", "predicate": "reported to", "object": "authority",
                   "source": "gdpr.md", "section": "Breaches"}],
        "metrics": {"input_tokens": 40, "output_tokens": 8, "total_tokens": 48,
                    "latency_ms": 20.0, "est_cost_usd": 0.0, "edges_used": 1, "model": "gemini-2.5-flash-lite"},
    }
    captured = {}

    def fake_graph_answer(question):
        captured["question"] = question
        return fake_result

    monkeypatch.setattr("chat.views.generate_graph_answer", fake_graph_answer)

    response = client.post(
        reverse("message-create", args=[conversation.id]),
        {"content": "Who is a breach reported to?", "technique": "graph"},
    )

    assert response.status_code == 302
    assistant = conversation.messages.get(role="assistant")
    assert assistant.technique == "graph"
    assert assistant.metadata["trace"][0]["subject"] == "breach"
    assert assistant.metadata["metrics"]["edges_used"] == 1
    assert captured["question"] == "Who is a breach reported to?"


def test_vectorless_technique_routes_and_stores_trace(client, user, monkeypatch):
    conversation = Conversation.objects.create(owner=user)
    fake_result = {
        "answer": "Within 72 hours [1].",
        "trace": [{"n": 1, "title": "Breaches", "path": "gdpr.md › Breaches", "source": "gdpr.md"}],
        "metrics": {"input_tokens": 30, "output_tokens": 6, "total_tokens": 36,
                    "latency_ms": 15.0, "est_cost_usd": 0.0, "sections_opened": 1, "model": "gemini-2.5-flash-lite"},
    }
    captured = {}

    def fake_answer(question):
        captured["question"] = question
        return fake_result

    monkeypatch.setattr("chat.views.generate_vectorless_answer", fake_answer)

    response = client.post(
        reverse("message-create", args=[conversation.id]),
        {"content": "How fast must a breach be reported?", "technique": "vectorless"},
    )

    assert response.status_code == 302
    assistant = conversation.messages.get(role="assistant")
    assert assistant.technique == "vectorless"
    assert assistant.metadata["trace"][0]["path"] == "gdpr.md › Breaches"
    assert assistant.metadata["metrics"]["sections_opened"] == 1
    assert captured["question"] == "How fast must a breach be reported?"


def test_multimodal_technique_routes_and_stores_trace(client, user, monkeypatch):
    conversation = Conversation.objects.create(owner=user)
    fake_result = {
        "answer": "Phishing [1].",
        "trace": [{"n": 1, "kind": "image", "page": 2, "text": "", "context": "chart", "image_b64": "AAA"}],
        "metrics": {"input_tokens": 200, "output_tokens": 5, "total_tokens": 205,
                    "latency_ms": 30.0, "est_cost_usd": 0.0, "evidence_used": 1, "model": "gemini-2.5-flash-lite"},
    }
    captured = {}

    def fake_answer(question):
        captured["question"] = question
        return fake_result

    monkeypatch.setattr("chat.views.generate_multimodal_answer", fake_answer)

    response = client.post(
        reverse("message-create", args=[conversation.id]),
        {"content": "Which incident category was most common?", "technique": "multimodal"},
    )

    assert response.status_code == 302
    assistant = conversation.messages.get(role="assistant")
    assert assistant.technique == "multimodal"
    assert assistant.metadata["trace"][0]["kind"] == "image"
    assert assistant.metadata["metrics"]["evidence_used"] == 1
    assert captured["question"] == "Which incident category was most common?"


def test_embedding_without_rerank_checkbox_disables_rerank(client, user, monkeypatch):
    conversation = Conversation.objects.create(owner=user)
    captured = {}

    def fake_answer(question, rerank_enabled=True):
        captured["rerank_enabled"] = rerank_enabled
        return {"answer": "a", "sources": [], "rerank_status": "off",
                "metrics": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2,
                            "latency_ms": 1.0, "est_cost_usd": 0.0, "embedding_dim": 3072,
                            "model": "gemini-2.5-flash-lite"}}

    monkeypatch.setattr("chat.views.generate_rag_answer", fake_answer)

    # No "rerank" field in POST => checkbox unchecked => rerank disabled.
    client.post(
        reverse("message-create", args=[conversation.id]),
        {"content": "q", "technique": "embedding"},
    )
    assert captured["rerank_enabled"] is False


def test_plain_technique_does_not_call_rag(client, user, monkeypatch):
    conversation = Conversation.objects.create(owner=user)
    monkeypatch.setattr("chat.gemini.generate_reply", Mock(return_value="Plain reply."))

    def fail(question):
        raise AssertionError("plain chat must not invoke embedding RAG")

    monkeypatch.setattr("chat.views.generate_rag_answer", fail)

    response = client.post(
        reverse("message-create", args=[conversation.id]),
        {"content": "hello", "technique": "plain"},
    )

    assert response.status_code == 302
    assert conversation.messages.get(role="assistant").technique == "plain"


def test_rename_conversation(client, user):
    conversation = Conversation.objects.create(owner=user)

    response = client.post(
        reverse("conversation-rename", args=[conversation.id]),
        {"title": "GDPR notes"},
    )

    conversation.refresh_from_db()
    assert conversation.title == "GDPR notes"
    assert response.status_code == 302


def test_delete_conversation(client, user):
    conversation = Conversation.objects.create(owner=user, title="Delete me")

    response = client.post(reverse("conversation-delete", args=[conversation.id]))

    assert not Conversation.objects.filter(id=conversation.id).exists()
    assert response.status_code == 302
    list_response = client.get(reverse("conversation-list"))
    assert b"Delete me" not in list_response.content


@pytest.mark.parametrize(
    ("method", "url_name", "data"),
    [
        ("get", "conversation-detail", None),
        ("post", "message-create", {"content": "Private question"}),
        ("post", "conversation-rename", {"title": "Stolen"}),
        ("post", "conversation-delete", None),
    ],
)
def test_cannot_access_others_conversation(client, method, url_name, data):
    owner = get_user_model().objects.create_user(username="other-owner")
    conversation = Conversation.objects.create(owner=owner)

    response = getattr(client, method)(
        reverse(url_name, args=[conversation.id]),
        data=data,
    )

    assert response.status_code == 404
    assert Conversation.objects.filter(id=conversation.id).exists()
