"""
FCM integration using Firebase Admin SDK (HTTP v1).
No legacy FIREBASE_SERVER_KEY/SENDER_ID required.
"""

from __future__ import annotations

import json
from typing import Any, Dict

import firebase_admin
from firebase_admin import messaging

from athena_logging import get_logger

logger = get_logger(__name__)

def send_fcm_message(token: str, title: str, body: str, source: str, result: Dict[str, Any]=None) -> str:
    """
    Send a push notification to a device via Firebase Cloud Messaging.

    :param token: The device token identifying the client.
    :param data: Dict that may include 'title' and 'body' plus custom fields.
    :return: The message ID string from FCM.
    """
    logger.info(f"Sending FCM message with data {title} {body} from {source}")
    if not firebase_admin._apps:
        raise RuntimeError(
            "Firebase Admin is not initialized. Set FIREBASE_CREDENTIALS to the "
            "path of your service account JSON."
        )

    notif = messaging.Notification(title=title, body=body)

    message = messaging.Message(
        token=token,
        notification=notif,
        data={"source": source, "result": json.dumps(result or {})},
    )

    logger.info(f"Message: {result}")
    return messaging.send(message)