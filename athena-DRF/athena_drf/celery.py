"""
Celery application for the Athena DRF project.

This module defines a Celery app instance which reads its configuration
from the Django settings.  It also autodiscovers tasks from all
installed Django apps so that you can define tasks in ``tasks.py`` files
throughout your project.  The Celery worker commands in the
docker‑compose file reference this module when starting workers.
"""

from __future__ import annotations

import os
from kombu import Exchange, Queue
from celery import Celery

import logging


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "athena_drf.settings")


# Create the Celery app and load configuration from Django settings.  The
# broker URL, result backend and other Celery options are read from
# settings via the CELERY_ prefix.
app = Celery("athena_drf")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks defined in any installed app.  You can create
# ``tasks.py`` in your apps (including api) and Celery will find them.
app.autodiscover_tasks()


# Define Celery task routes
app.conf.task_routes = {
    "runs.execute_graph": {
        "queue": "public",  # default; DRF overrides per send_task
    },
    "gateway.dispatch_push": {
        "queue": "gateway",
    },
}

# Define exchanges
app.conf.task_queues = (
    Queue("public", Exchange("public"), routing_key="public"),
    Queue("sensitive", Exchange("sensitive"), routing_key="sensitive"),
    Queue("gateway", Exchange("gateway"), routing_key="gateway"),
)


@app.task(bind=True)
def debug_task(self, *args, **kwargs):  # type: ignore[no-redef]
    """A simple debug task that prints its request context."""
    print(f"Request: {self.request!r}")