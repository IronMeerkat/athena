"""
Celery application for the Athena LangChain workers.

The Celery app defined here reads configuration from environment
variables or from a ``.env`` file.  It autodiscovers tasks in the
``tasks`` package.  In docker-compose the workers explicitly specify
which queue they listen on (``public`` or ``sensitive``).  You can
configure additional queues via Celery's routing options.
"""

from __future__ import annotations

import os
import logging

from celery import Celery
from celery.signals import setup_logging as celery_setup_logging
from dotenv import load_dotenv
from athena_logging import configure_logging

# Load environment variables from a .env file if present.  This allows
# customizing the broker URL, result backend and other options without
# modifying source code.
load_dotenv()

app = Celery("athena_langchain")

# Configure the Celery app from environment variables prefixed with
# ``CELERY_``.  For example, set ``CELERY_BROKER_URL`` to
# ``amqp://admin:admin@rabbitmq:5672//`` in your docker-compose environment to point
# Celery at the correct RabbitMQ instance.
app.config_from_object({
    "broker_url": os.getenv("CELERY_BROKER_URL", "amqp://admin:admin@rabbitmq:5672//"),
    "result_backend": os.getenv("CELERY_RESULT_BACKEND", "rpc://"),
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,
    "timezone": os.getenv("CELERY_TIMEZONE", "America/New_York"),
})

# Prevent Celery from hijacking the root logger; we configure it ourselves
app.conf.worker_hijack_root_logger = False


def _set_library_log_levels() -> None:
    """Reduce noise from network and Celery-related libraries.

    Sets common noisy libraries to WARNING so only important messages surface.
    """
    noisy_logger_names = (
        "httpx",
        "httpcore",
        "urllib3",
        "celery",
        "kombu",
        "amqp",
        "billiard",
    )
    for logger_name in noisy_logger_names:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

@celery_setup_logging.connect  # type: ignore[misc]
def _configure_celery_logging(**kwargs):  # noqa: D401
    configure_logging(force=True)
    _set_library_log_levels()


# Also configure at import time for early logs
configure_logging()
_set_library_log_levels()

# Autodiscover tasks from the ``tasks`` package.  Celery will import any
# ``tasks.py`` modules found within ``athena_langchain`` and its
# subpackages.
app.autodiscover_tasks(
    packages=["athena_langchain"],
    related_name="tasks",
)