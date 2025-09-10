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
def dispatch_push(token: str, title: str, body: str, source: str, result: Dict[str, Any]=None) -> None:
    """
    Dispatch a push payload to Android frontends.
    """

    try:
        send_fcm_message(token, title, body, source, result)
    except Exception as e:
        logger.exception(f"Error sending FCM message, data: {token} {title} {body} from {source}")


@shared_task(name="recieved.telegram")
def recieved_telegram(chat_id: str, text: str) -> None:
    """
    Recieved a message from Telegram.
    """
    logger.debug(f"Recieved a message from Telegram: {text} in chat {chat_id}")
    chat = Chat.objects.get(id=chat_id)
    chat.messages.create(
        role=ChatMessage.ROLE_ASSISTANT,
        content=text,
    )
    chat.save(update_fields=["updated_at"])
    send_telegram_message(chat.telegram_chat_id, text)