from __future__ import annotations

import requests
from django.conf import settings


def send_telegram_message(chat_id: int, text: str) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    resp = requests.post(url, json=payload, timeout=10)
    print(resp.json())



def send_chat_action(chat_id: int, action: str = "typing") -> None:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")
    url = f"https://api.telegram.org/bot{token}/sendChatAction"
    payload = {"chat_id": chat_id, "action": action}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass


