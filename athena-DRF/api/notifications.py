"""
Placeholder module for Firebase Cloud Messaging (FCM) integration.

This module defines a thin wrapper around sending push notifications via
Firebase.  The actual implementation is omitted in this boilerplate.
When you're ready to integrate FCM, install the ``firebase-admin``
package and implement ``send_fcm_message`` to construct and send push
notifications to client devices using your Firebase server key.
"""

from __future__ import annotations

from typing import Any, Dict

from django.conf import settings


def send_fcm_message(token: str, data: Dict[str, Any]) -> None:
    """
    Send a push notification to a device via Firebase Cloud Messaging.

    :param token: The device token identifying the client.
    :param data: The data payload to send.  Typically this includes
        notification title/body and any custom fields.
    :raises RuntimeError: if Firebase credentials are not configured.
    """
    if not settings.FIREBASE_SERVER_KEY or not settings.FIREBASE_SENDER_ID:
        raise RuntimeError(
            "Firebase is not configured. Provide FIREBASE_SERVER_KEY and"
            " FIREBASE_SENDER_ID in your environment or settings."
        )
    # Placeholder: implement your FCM logic here.  For example, using
    # firebase_admin.messaging to send a Message object.  You might do
    # something like:
    #
    # from firebase_admin import messaging
    # message = messaging.Message(
    #     token=token,
    #     data=data,
    #     notification=messaging.Notification(title=data.get("title"), body=data.get("body")),
    # )
    # response = messaging.send(message)
    # return response
    raise NotImplementedError("FCM integration is not implemented in this boilerplate.")