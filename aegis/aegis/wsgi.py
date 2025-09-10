"""
WSGI config for Athena DRF project.

This file exposes the WSGI callable as a module-level variable named
``application``.  It is used by Django's development server and by any
WSGI server such as Gunicorn in a production deployment.  If you plan to
run the gateway using ASGI, refer to ``asgi.py`` instead.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aegis.settings")

application = get_wsgi_application()