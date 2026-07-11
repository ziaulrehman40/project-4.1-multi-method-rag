from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from . import gemini
from .models import Conversation, Message


def _owned_conversation(request, conversation_id):
    return get_object_or_404(
        Conversation,
        id=conversation_id,
        owner=request.user,
    )


@login_required
@require_GET
def conversation_list(request):
    conversations = Conversation.objects.filter(owner=request.user)
    return render(
        request,
        "chat/conversation_list.html",
        {"conversations": conversations},
    )


@login_required
@require_POST
def conversation_create(request):
    conversation = Conversation.objects.create(owner=request.user)
    return redirect("conversation-detail", conversation_id=conversation.id)


@login_required
@require_GET
def conversation_detail(request, conversation_id):
    conversation = _owned_conversation(request, conversation_id)
    return render(
        request,
        "chat/conversation_detail.html",
        {"conversation": conversation, "messages": conversation.messages.all()},
    )


@login_required
@require_POST
def message_create(request, conversation_id):
    conversation = _owned_conversation(request, conversation_id)
    content = request.POST.get("content", "").strip()
    if not content:
        return HttpResponseBadRequest("Message content is required.")

    user_message = Message.objects.create(
        conversation=conversation,
        role="user",
        content=content,
    )
    history = list(conversation.messages.values("role", "content"))
    reply = gemini.generate_reply(history)
    assistant_message = Message.objects.create(
        conversation=conversation,
        role="assistant",
        content=reply,
    )
    conversation.save(update_fields=["updated_at"])

    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "chat/_message.html",
            {"messages": [user_message, assistant_message]},
        )
    return redirect("conversation-detail", conversation_id=conversation.id)


@login_required
@require_POST
def conversation_rename(request, conversation_id):
    conversation = _owned_conversation(request, conversation_id)
    title = request.POST.get("title", "").strip()
    if not title:
        return HttpResponseBadRequest("Title is required.")
    conversation.title = title[:200]
    conversation.save(update_fields=["title", "updated_at"])
    return redirect("conversation-detail", conversation_id=conversation.id)


@login_required
@require_POST
def conversation_delete(request, conversation_id):
    conversation = _owned_conversation(request, conversation_id)
    conversation.delete()
    return redirect("conversation-list")

