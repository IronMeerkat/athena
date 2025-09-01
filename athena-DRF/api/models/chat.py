from __future__ import annotations

from django.conf import settings
from django.db import models


class Chat(models.Model):
    """A chat session identified by a client-provided session_id.

    We store chats keyed by the WebSocket session identifier so that
    Android can resume the same thread later.
    """

    id = models.CharField(primary_key=True, max_length=64)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chats",
    )
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat"
        ordering = ["-updated_at"]

    def __str__(self) -> str:  # pragma: no cover - debug display
        return f"Chat<{self.id}>"


class ChatMessage(models.Model):
    """A single message within a chat thread."""

    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_CHOICES = (
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
    )

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_message"
        ordering = ["created_at", "id"]

    def __str__(self) -> str:  # pragma: no cover - debug display
        return f"ChatMessage<{self.chat_id} {self.role}>"


