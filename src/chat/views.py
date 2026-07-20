import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from kg.answer import GraphAnswerError
from kg.answer import answer as generate_graph_answer
from rag.answer import AnswerError
from rag.answer import answer as generate_rag_answer
from rag.embeddings import EmbeddingError
from multimodal.answer import MultimodalAnswerError
from multimodal.answer import answer as generate_multimodal_answer
from vectorless.answer import VectorlessAnswerError
from vectorless.answer import answer as generate_vectorless_answer

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
    if len(content) > settings.MAX_QUESTION_CHARS:  # guardrail: bound prompt size
        return HttpResponseBadRequest(
            f"Message too long (max {settings.MAX_QUESTION_CHARS} characters)."
        )

    logger.info(
        "message.received conversation_id=%s user_id=%s content_chars=%d htmx=%s",
        conversation.id,
        request.user.id,
        len(content),
        request.headers.get("HX-Request") == "true",
    )
    technique = request.POST.get("technique", "plain")
    if technique not in ("plain", "embedding", "graph", "vectorless", "multimodal"):
        technique = "plain"

    try:
        with transaction.atomic():
            user_message = Message.objects.create(
                conversation=conversation,
                role="user",
                content=content,
                technique=technique,
            )
            metadata = None
            if technique == "embedding":
                # Embedding-RAG: retrieve + (optional) rerank + cited generation on the
                # latest question. Rerank is a checkbox (extra LLM call; can be turned off).
                rerank_enabled = request.POST.get("rerank") == "on"
                result = generate_rag_answer(content, rerank_enabled=rerank_enabled)
                reply = result["answer"]
                metadata = {
                    "sources": result["sources"],
                    "rerank_status": result["rerank_status"],
                    "metrics": result["metrics"],
                }
                history = []
            elif technique == "graph":
                # Knowledge-graph RAG: seed + traverse the extracted graph, cited answer
                # with a node/edge trace (rendered as an interactive graph in the UI).
                result = generate_graph_answer(content)
                reply = result["answer"]
                metadata = {"trace": result["trace"], "metrics": result["metrics"]}
                history = []
            elif technique == "vectorless":
                # Vectorless RAG: LLM navigates the document tree to pick sections, then
                # answers from them. Trace = the navigation path (sections opened).
                result = generate_vectorless_answer(content)
                reply = result["answer"]
                metadata = {"trace": result["trace"], "metrics": result["metrics"]}
                history = []
            elif technique == "multimodal":
                # Multimodal RAG: cross-modal retrieval over the PDF (text/tables/figures);
                # the vision model reads retrieved figures. Trace carries the evidence used.
                result = generate_multimodal_answer(content)
                reply = result["answer"]
                metadata = {"trace": result["trace"], "metrics": result["metrics"]}
                history = []
            else:
                history = list(conversation.messages.values("role", "content"))
                reply = gemini.generate_reply(history)
            assistant_message = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=reply,
                technique=technique,
                metadata=metadata,
            )
            conversation.save(update_fields=["updated_at"])
    except (
        gemini.GeminiError,
        AnswerError,
        EmbeddingError,
        GraphAnswerError,
        VectorlessAnswerError,
        MultimodalAnswerError,
    ):
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
            "chat/_message_turn.html",
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
