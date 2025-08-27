"""
Athena DRF project package.

The ``athena_drf`` package contains the Django settings and ASGI/WSGI entry
points for the gateway service.  It also exposes a Celery application via
the ``celery_app`` attribute so that other modules (such as tasks or
management commands) can easily import the configured Celery instance.
"""

from .celery import app as celery_app  # noqa: F401

__all__ = ("celery_app",)