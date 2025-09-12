
import os
from kombu import Exchange, Queue
from celery import Celery, shared_task as _shared_task
from celery.signals import setup_logging as celery_setup_logging
from celery import signals
import threading
import asyncio
from athena_settings import settings
from athena_logging import configure_logging

app = Celery("athena")

app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    timezone=settings.CELERY_TIMEZONE,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
)

app.autodiscover_tasks()

app.conf.worker_hijack_root_logger = settings.CELERY_WORKER_HIJACK_ROOT_LOGGER


@celery_setup_logging.connect  # type: ignore[misc]
def _configure_celery_logging(**kwargs):  # noqa: D401
    # Reconfigure each time Celery initializes logging (main and child procs)
    configure_logging(force=True)

configure_logging()


def shared_task(*args, **kwargs):

    """
    Decorator to make a celery's shared_task decorator async-friendly.
    """

    def decorator(task_func):

        def inner(*a, **k):
            if asyncio.iscoroutinefunction(task_func):
                return asyncio.run(task_func(*a, **k))
            return task_func(*a, **k)

        return _shared_task(*args, **kwargs)(inner)

    return decorator


