"""
Celery tasks for the Athena DRF API app.

All DRF interactions with workers or external push providers are
performed via Celery queues. DRF never imports worker code directly.
"""

from celery import shared_task
from typing import Any, Dict


from api.integrations.telegram import send_telegram_message
from api.models import Chat, ChatMessage

from django.conf import settings

from .notifications import send_fcm_message

from athena_logging import get_logger

logger = get_logger(__name__)


@shared_task
def example_background_task(x: int, y: int) -> int:
    """
    A trivial example task that adds two numbers together.

    This function exists solely to illustrate how to define a task.  In a
    real application you might perform I/O, long‑running computations or
    other work here.
    """
    return x + y


@shared_task(name="gateway.dispatch_push")
def dispatch_push(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch a push payload to browser and/or Android frontends.

    Expected data:
      {"target": "browser|android|all", "kind": "info|block_signal|unblock_signal",
       "title": str, "body": str, "meta": {..}, "device_id": optional}
    """
    target = str(data.get("target", "all"))
    kind = str(data.get("kind", "info"))
    title = str(data.get("title", ""))
    body = str(data.get("body", ""))
    meta = data.get("meta") or {}
    result: Dict[str, Any] = {"sent": []}
    logger.info(f"Dispatching push: {data}")

    # Android via FCM (if configured)
    if target in ("android", "all"):
        token = str(data.get('device_id') or "")
        if token:
            try:
                send_fcm_message(token, {
                    "kind": kind,
                    "title": title,
                    "body": body,
                    "meta": meta,
                })
                result["sent"].append("android")
            except Exception as e:  # noqa: BLE001
                result.setdefault("errors", []).append(str(e))

    # Browser extension broadcast is left as a TODO: integrate via a
    # push/broadcast mechanism exposed by the extension backend if needed.
    if target in ("browser", "all"):
        # Placeholder: record intent
        result["sent"].append("browser")

    return result

@shared_task(name="recieved.telegram")
def recieved_telegram(chat_id: str, text: str) -> None:
    """
    Recieved a message from Telegram.
    """
    print(f"Recieved a message from Telegram: {text} in chat {chat_id}")
    chat = Chat.objects.get(id=chat_id)
    chat.messages.create(
        role=ChatMessage.ROLE_ASSISTANT,
        content=text,
    )
    chat.save(update_fields=["updated_at"])
    send_telegram_message(chat.telegram_chat_id, text)