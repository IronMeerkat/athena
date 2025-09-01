from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Chat, ChatMessage


class ChatsListView(APIView):
    """GET /api/chats — list chats for the current user.

    Returns a minimal list of chats with last message preview.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: HttpRequest) -> Response:  # type: ignore[override]
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        chats = (
            Chat.objects.filter(user=user)
            .prefetch_related("messages")
            .order_by("-updated_at")
        )
        def serialize_chat(chat: Chat) -> dict[str, Any]:
            last = chat.messages.order_by("-created_at").first()
            return {
                "id": chat.id,
                "title": chat.title or "",
                "updated_at": chat.updated_at.isoformat(),
                "last_message": {
                    "role": getattr(last, "role", None),
                    "content": getattr(last, "content", None),
                    "created_at": getattr(last, "created_at", None).isoformat() if last else None,
                } if last else None,
            }

        return Response({"chats": [serialize_chat(c) for c in chats]})


class ChatMessagesView(APIView):
    """GET /api/chats/{chat_id}/messages — full message history for a chat."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: HttpRequest, chat_id: str) -> Response:  # type: ignore[override]
        user = request.user if request.user.is_authenticated else None
        if not user:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            chat = Chat.objects.get(id=chat_id, user=user)
        except Chat.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        messages = chat.messages.order_by("created_at", "id")
        return Response(
            {
                "chat": {
                    "id": chat.id,
                    "title": chat.title or "",
                    "created_at": chat.created_at.isoformat(),
                    "updated_at": chat.updated_at.isoformat(),
                },
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in messages
                ],
            }
        )


