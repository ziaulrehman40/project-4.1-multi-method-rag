from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from chat.models import Conversation, Message


pytestmark = pytest.mark.django_db


def test_login_required_redirects(client):
    client.logout()

    response = client.get(reverse("conversation-list"))

    assert response.status_code == 302
    assert response.url == f'{reverse("login")}?next=/'


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
