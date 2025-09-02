from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from django.conf import settings

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from api.models import User


class TelegramWebhookAuthentication(BaseAuthentication):
    """Authenticate Telegram webhook requests as the mapped User.

    - Verifies X-Telegram-Bot-Api-Secret-Token against settings.TELEGRAM_WEBHOOK_SECRET
    - Extracts telegram sender id from update payload
    - Loads the corresponding User via User.telegram_user_id
    """

    def authenticate(self, request) -> Optional[Tuple[User, None]]:  # type: ignore[override]
        got = request.META.get("HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN", "")
        if got != settings.SECRET_KEY:
            raise AuthenticationFailed("Invalid secret key")

        data: Dict[str, Any] = request.data or {}
        message = data.get("message") or data.get("edited_message") or {}
        from_user = message.get("from") or {}
        telegram_user_id = from_user.get("id")
        if not telegram_user_id:
            return None

        try:
            user = User.objects.get(telegram_user_id=telegram_user_id)
        except User.DoesNotExist:
            return None

        request.telegram_user_id = telegram_user_id
        request.user = user
        return (user, None)


