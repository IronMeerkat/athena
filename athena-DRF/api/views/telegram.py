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
from athena_drf.permissions import IsTelegramWebhookAllowed
from athena_drf.authentication import TelegramWebhookAuthentication
from api.integrations.telegram import send_telegram_message, send_chat_action
from django.http import HttpResponseServerError


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
            print(update_data)
            update = Update.de_json(update_data, None)

            if not update.message or not update.message.text:
                return Response(status=status.HTTP_200_OK)

            user_message = update.message.text

        except Exception as e:
            return Response({"error": "Invalid webhook data"}, status=status.HTTP_400_BAD_REQUEST)

        normalized_text = (user_message or "").strip()
        starts_new_chat = normalized_text.startswith("/start")

        if starts_new_chat:
            chat = Chat.objects.create(
                id=str(uuid.uuid4()),
                user=request.user,
                is_telegram=True,
                title="",
            )
        else:
            chat = Chat.objects.filter(user=request.user, is_telegram=True).order_by("-updated_at").first()
            if not chat:
                chat = Chat.objects.create(
                    id=str(uuid.uuid4()),
                    user=request.user,
                    is_telegram=True,
                    title="",
                )

        if chat.user.id != request.user.id:
            raise HttpResponseServerError("Chat user does not match request user")

        chat.telegram_chat_id = update.message.chat.id
        chat.save(update_fields=["telegram_chat_id"])

        # Save user message to chat
        chat.messages.create(
            role="user",
            content=user_message,
        )

        # Send to Athena via Celery
        # Use stable run/session id so RMQ routing matches websocket pattern
        run_id = f"telegram:{chat.id}"

        # Build manifest with chat context
        manifest = self.manifest.copy()
        manifest["metadata"] = {
            "chat_id": chat.id,
            "telegram_user_id": request.user.telegram_user_id,
            "actor": f"telegram_user_{request.user.telegram_user_id}"
        }

        # Send task to Celery
        payload = {
            "user_message": user_message,
            "session_id": f"telegram:{chat.id}",
        }
        print(payload)
        manifest.setdefault("metadata", {})["session_id"] = payload["session_id"]
        celery_app.send_task(
            "runs.execute_graph",
            args=[run_id, self.agent_name, payload, manifest],
            queue=manifest["queue"],
        )

        return Response(status=status.HTTP_200_OK)