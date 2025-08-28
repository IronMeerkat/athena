"""
FCM integration using Firebase Admin SDK (HTTP v1).
No legacy FIREBASE_SERVER_KEY/SENDER_ID required.
"""

from __future__ import annotations

from typing import Any, Dict

import firebase_admin
from firebase_admin import messaging


def send_fcm_message(token: str, data: Dict[str, Any]) -> str:
    """
    Send a push notification to a device via Firebase Cloud Messaging.

    :param token: The device token identifying the client.
    :param data: Dict that may include 'title' and 'body' plus custom fields.
    :return: The message ID string from FCM.
    """
    if not firebase_admin._apps:
        raise RuntimeError(
            "Firebase Admin is not initialized. Set FIREBASE_CREDENTIALS to the "
            "path of your service account JSON."
        )

    title = data.get("title")
    body = data.get("body")
    notif = messaging.Notification(title=str(title) if title else None,
                                   body=str(body) if body else None)

    # FCM data payload must be str->str
    payload = {
        k: str(v)
        for k, v in data.items()
        if k not in {"title", "body"} and v is not None
    }

    message = messaging.Message(
        token=token,
        notification=notif if (title or body) else None,
        data=payload if payload else None,
    )
    return messaging.send(message)