from django.urls import path

from . import views


urlpatterns = [
    path("", views.conversation_list, name="conversation-list"),
    path("conversations/", views.conversation_create, name="conversation-create"),
    path(
        "conversations/<int:conversation_id>/",
        views.conversation_detail,
        name="conversation-detail",
    ),
    path(
        "conversations/<int:conversation_id>/messages/",
        views.message_create,
        name="message-create",
    ),
    path(
        "conversations/<int:conversation_id>/rename/",
        views.conversation_rename,
        name="conversation-rename",
    ),
    path(
        "conversations/<int:conversation_id>/delete/",
        views.conversation_delete,
        name="conversation-delete",
    ),
]

