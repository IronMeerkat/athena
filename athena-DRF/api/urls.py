"""
URL routes for the API app.

This module defines REST endpoints served under the ``/api/`` path.  The
actual WebSocket routes are defined in ``routing.py`` and not exposed via
the standard Django URL configuration.
"""
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

from django.urls import path
from . import views


urlpatterns = [
    # Health check
    path("ping/", views.PingView.as_view(), name="api-ping"),

    # Runs API
    path("runs/", views.RunsCreateView.as_view(), name="api-runs-create"),
    path("runs/<str:run_id>/events", views.RunEventsSSEView.as_view(), name="api-runs-events"),

    # Device flow
    path("device/attempt", views.DeviceAttemptView.as_view(), name="api-device-attempt"),
    path("device/permit", views.DevicePermitView.as_view(), name="api-device-permit"),

    # Chats API
    path("chats", views.ChatsListView.as_view(), name="api-chats-list"),
    path("chats/<str:chat_id>/messages", views.ChatMessagesView.as_view(), name="api-chat-messages"),

    # Telegram API
    path("telegram", views.TelegramWebhookView.as_view(), name="api-telegram-basic"),

    # JWT auth
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]