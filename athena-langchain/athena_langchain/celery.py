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

from celery import Celery
from dotenv import load_dotenv

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

# Autodiscover tasks from the ``tasks`` package.  Celery will import any
# ``tasks.py`` modules found within ``athena_langchain`` and its
# subpackages.
app.autodiscover_tasks(
    packages=["athena_langchain"],
    related_name="tasks",
)