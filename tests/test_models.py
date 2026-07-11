import pytest

from chat.models import Conversation, Message


pytestmark = pytest.mark.django_db


def test_conversation_defaults(user):
    conversation = Conversation.objects.create(owner=user)

    assert conversation.title == "New conversation"
    assert conversation.owner == user
    assert conversation.created_at is not None
    assert conversation.updated_at is not None


def test_messages_ordered_by_created(user):
    conversation = Conversation.objects.create(owner=user)
    first = Message.objects.create(
        conversation=conversation,
        role="user",
        content="What is PCI DSS?",
    )
    second = Message.objects.create(
        conversation=conversation,
        role="assistant",
        content="It is a payment-card security standard.",
    )

    assert list(conversation.messages.all()) == [first, second]


def test_delete_conversation_cascades_messages(user):
    conversation = Conversation.objects.create(owner=user)
    Message.objects.create(conversation=conversation, role="user", content="Hello")

    conversation.delete()

    assert Message.objects.count() == 0

