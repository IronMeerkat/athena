"""
WebSocket routing for the API app.

Channels requires you to define routing patterns for WebSocket
connections.  This module defines the URL patterns for WebSocket
endpoints.  The consumers referenced here live in ``consumers.py`` and
are simple stubs you should replace with your own real‑time logic.
"""

from django.urls import path

from .websocket_consumers import AppealsConsumer, EchoConsumer, JournalConsumer

# List of websocket URL patterns.  Each path here will be routed
# exclusively for WebSocket connections via the ASGI application defined
# in ``athena_drf.asgi.application``.
websocket_urlpatterns = [
    path("", EchoConsumer.as_asgi(), name="ws-echo"),
    path("ws/appeals/<str:event_id>", AppealsConsumer.as_asgi(), name="ws-appeals"),
    path("ws/journal/<str:session_id>", JournalConsumer.as_asgi(), name="ws-journal"),
]