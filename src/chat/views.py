import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from . import gemini
from .models import Conversation, Message


logger = logging.getLogger(__name__)


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
    logger.debug("conversation.list user_id=%s", request.user.id)
    return render(
        request,
        "chat/conversation_list.html",
        {"conversations": conversations},
    )


@login_required
@require_POST
def conversation_create(request):
    conversation = Conversation.objects.create(owner=request.user)
    logger.info(
        "conversation.created conversation_id=%s user_id=%s",
        conversation.id,
        request.user.id,
    )
    return redirect("conversation-detail", conversation_id=conversation.id)


@login_required
@require_GET
def conversation_detail(request, conversation_id):
    conversation = _owned_conversation(request, conversation_id)
    logger.debug(
        "conversation.opened conversation_id=%s user_id=%s",
        conversation.id,
        request.user.id,
    )
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
        logger.warning(
            "message.rejected conversation_id=%s user_id=%s reason=blank",
            conversation.id,
            request.user.id,
        )
        return HttpResponseBadRequest("Message content is required.")

    logger.info(
        "message.received conversation_id=%s user_id=%s content_chars=%d htmx=%s",
        conversation.id,
        request.user.id,
        len(content),
        request.headers.get("HX-Request") == "true",
    )
    try:
        with transaction.atomic():
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
    except gemini.GeminiError:
        logger.warning(
            "message.failed conversation_id=%s user_id=%s reason=gemini_error",
            conversation.id,
            request.user.id,
        )
        error = "We could not get a reply from Gemini. Your message was not saved; please try again."
        if request.headers.get("HX-Request") == "true":
            return render(request, "chat/_error.html", {"error": error}, status=502)
        return render(
            request,
            "chat/conversation_detail.html",
            {
                "conversation": conversation,
                "messages": conversation.messages.all(),
                "error": error,
                "draft_content": content,
            },
            status=502,
        )

    logger.info(
        "message.persisted conversation_id=%s user_id=%s user_message_id=%s assistant_message_id=%s history_messages=%d",
        conversation.id,
        request.user.id,
        user_message.id,
        assistant_message.id,
        len(history),
    )
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
    logger.info(
        "conversation.renamed conversation_id=%s user_id=%s title_chars=%d",
        conversation.id,
        request.user.id,
        len(conversation.title),
    )
    return redirect("conversation-detail", conversation_id=conversation.id)


@login_required
@require_POST
def conversation_delete(request, conversation_id):
    conversation = _owned_conversation(request, conversation_id)
    deleted_id = conversation.id
    conversation.delete()
    logger.info(
        "conversation.deleted conversation_id=%s user_id=%s",
        deleted_id,
        request.user.id,
    )
    return redirect("conversation-list")
