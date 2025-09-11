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
from celery.signals import setup_logging as celery_setup_logging
from athena_logging import configure_logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aegis.settings")


# Create the Celery app and load configuration from Django settings.  The
# broker URL, result backend and other Celery options are read from
# settings via the CELERY_ prefix.
app = Celery("aegis")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks defined in any installed app.  You can create
# ``tasks.py`` in your apps (including api) and Celery will find them.
app.autodiscover_tasks()
# Ensure Celery does not override our root logger configuration
app.conf.worker_hijack_root_logger = False


# Configure logging for worker processes using Athena's logger
@celery_setup_logging.connect  # type: ignore[misc]
def _configure_celery_logging(**kwargs):  # noqa: D401
    # Reconfigure each time Celery initializes logging (main and child procs)
    configure_logging(force=True)


# Also configure at import time so early imports use our logger
configure_logging()



# Define Celery task routes
app.conf.task_routes = {
    "runs.execute_graph": {
        "queue": "public",  # default; DRF overrides per send_task
    },
    "gateway.dispatch_push": {
        "queue": "gateway",
    },
    "recieved.telegram": {
        "queue": "gateway",
    },
    "telegram_agent_task": {
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