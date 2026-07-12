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
    assert b"Explain SOC 2 controls." in response.content
    assert b"SOC 2 controls support trust service criteria." in response.content


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
