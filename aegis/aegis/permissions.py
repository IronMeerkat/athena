from __future__ import annotations

from typing import Any, Dict

from django.conf import settings
from rest_framework.permissions import BasePermission

from api.models import Chat, User


class IsTelegramWebhookAllowed(BasePermission):
    """Allow Telegram webhook requests only if:
    - The shared secret header matches settings.TELEGRAM_WEBHOOK_SECRET, and
    - The Telegram sender is either unlinked (new chat) or matches the existing chat's linked user.

    This guards association of Telegram user IDs to Users and prevents cross-user posting to chats.
    """

    message = "Forbidden Telegram webhook request"

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        expected = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
        got = request.META.get("HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN", "")
        if not expected or got != expected:
            return False

        data: Dict[str, Any] = request.data or {}
        message = data.get("message") or data.get("edited_message") or {}
        from_user = message.get("from") or {}
        telegram_user_id = from_user.get("id")
        if not telegram_user_id:
            return False

        # Stash for the view to reuse without reparsing
        setattr(request, "telegram_user_id", telegram_user_id)

        chat_id = getattr(view, "kwargs", {}).get("chat_id") or request.parser_context.get("kwargs", {}).get("chat_id") if hasattr(request, "parser_context") else None
        if not chat_id:
            # If the route doesn't specify a chat, allow; view will decide how to create one
            return True

        try:
            chat = Chat.objects.select_related("user").get(id=chat_id)
        except Chat.DoesNotExist:
            # New chat can be created and associated
            return True

        if chat.user_id is None:
            return True

        try:
            user = User.objects.get(id=chat.user_id)
        except User.DoesNotExist:
            # Stale link; allow so view can repair
            return True

        return user.telegram_user_id == telegram_user_id


