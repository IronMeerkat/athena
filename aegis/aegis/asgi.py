"""
ASGI config for Athena DRF project.

It exposes the ASGI callable as a module-level variable named ``application``.

This file wires up both HTTP handling (via Django's ``get_asgi_application``)
and WebSocket handling (via Channels).  WebSockets are routed through the
``api.routing.websocket_urlpatterns`` module.  You should extend that
module with your own consumers as you build real‑time features.
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aegis.settings")

# Import the websocket routing from the api app.  This import is placed
# after setting the DJANGO_SETTINGS_MODULE to ensure Django is properly
# configured.  Without this, consumers may fail to import database models
# or other Django modules.
django_asgi_app = get_asgi_application()

# Import websocket routing only after Django apps are loaded
from api import routing as api_routing  # noqa: E402

# The ProtocolTypeRouter determines which consumer should handle each
# incoming connection based on the protocol.  HTTP requests are passed to
# Django and WebSocket connections are passed through Channels.
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(api_routing.websocket_urlpatterns)
        ),
    }
)