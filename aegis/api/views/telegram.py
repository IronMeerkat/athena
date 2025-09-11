import json
import time
import uuid
from typing import Any, Dict
import os, hmac, hashlib

from celery import current_app as celery_app
from django.conf import settings
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from kombu import Connection, Exchange, Queue
from kombu.exceptions import KombuError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from telegram import Update
from telegram.ext import Application, ApplicationBuilder

from api.models import Chat, User
from api.agents import telegram_agent
from aegis.permissions import IsTelegramWebhookAllowed
from aegis.authentication import TelegramWebhookAuthentication
from api.integrations.telegram import send_telegram_message
from django.http import HttpResponseServerError

from athena_logging import get_logger

logger = get_logger(__name__)


class TelegramWebhookView(APIView):

    authentication_classes = [TelegramWebhookAuthentication]
    permission_classes = [IsAuthenticated]

    agent_name = "journaling"

    manifest = {
            "agent_ids": ["journaling"],
            "tool_ids": [],
            "memory_namespaces": [],
            "queue": "sensitive",
        }
    def post(self, request: HttpRequest) -> HttpResponse:
        # Parse Telegram webhook data (permission has already validated secret and cached sender id)
        try:
            update_data = request.data
            update = Update.de_json(update_data, None)

            logger.info(f"Update: {update}")

            if not update.message or not update.message.text:
                return Response(status=status.HTTP_200_OK)

            user_message = update.message.text

        except Exception as e:
            return Response({"error": "Invalid webhook data"}, status=status.HTTP_400_BAD_REQUEST)

        normalized_text = (user_message or "").strip()

        celery_app.send_task(
            "telegram_agent_task",
            kwargs={"telegram_chat_id": update.message.chat.id,
                    "text": normalized_text},
            queue="gateway",
        )

        return Response(status=status.HTTP_200_OK)
