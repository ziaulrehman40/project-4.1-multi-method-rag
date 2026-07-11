from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "updated_at")
    list_filter = ("updated_at",)
    search_fields = ("title", "owner__username")
    inlines = (MessageInline,)

