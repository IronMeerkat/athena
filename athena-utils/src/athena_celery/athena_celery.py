
import os
import signal
import sys
import time
from kombu import Exchange, Queue
from celery import Celery, shared_task as _shared_task
from celery.signals import setup_logging as celery_setup_logging
from celery import signals
import threading
import asyncio
import nest_asyncio
from athena_settings import settings
from athena_logging import configure_logging, get_logger
from .cleanup_old_workers import cleanup_old_workers

logger = get_logger(__name__)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

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

# Configure worker to handle signals properly and prevent resource issues
app.conf.worker_disable_rate_limits = True
app.conf.worker_prefetch_multiplier = 1  # Only prefetch one task at a time
app.conf.task_acks_late = True  # Acknowledge tasks only after completion
app.conf.worker_max_tasks_per_child = 100  # Restart workers more frequently to prevent issues
app.conf.worker_max_memory_per_child = 200000  # Restart workers if they use too much memory (200MB)
app.conf.task_soft_time_limit = 300  # 5 minutes soft limit
app.conf.task_time_limit = 600  # 10 minutes hard limit
app.conf.task_reject_on_worker_lost = True  # Reject tasks if worker is lost
app.conf.task_ignore_result = True  # Don't store task results unless explicitly needed

# Connection resilience settings
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_connection_retry = True
app.conf.broker_connection_max_retries = 10
app.conf.broker_connection_retry_delay = 5.0
app.conf.broker_heartbeat = 30  # Send heartbeat every 30 seconds
app.conf.broker_pool_limit = 10
app.conf.result_backend_transport_options = {
    'retry_policy': {
        'timeout': 5.0,
        'max_retries': 3,
    }
}
app.conf.broker_transport_options = {
    'retry_policy': {
        'timeout': 5.0,
        'max_retries': 3,
    },
    'confirm_publish': True,
    'max_retries': 3,
    'interval_start': 0,
    'interval_step': 0.2,
    'interval_max': 0.2,
}


@celery_setup_logging.connect  # type: ignore[misc]
def _configure_celery_logging(**kwargs):  # noqa: D401
    # Reconfigure each time Celery initializes logging (main and child procs)
    configure_logging(force=True)

configure_logging()


# Global flag to track shutdown state
_shutdown_requested = False

def handle_shutdown_signal(signum, frame):
    """Handle shutdown signals gracefully"""
    global _shutdown_requested
    if not _shutdown_requested:
        _shutdown_requested = True
        logger.info(f"Received signal {signum}. Initiating graceful shutdown...")

        # Give running tasks time to complete
        logger.debug("Waiting 2 seconds for running tasks to complete...")
        time.sleep(2)

        # Terminate the app
        if hasattr(app, 'control'):
            try:
                logger.debug("Shutting down Celery app...")
                app.control.shutdown()
            except Exception as e:
                logger.error(f"Error during app shutdown: {e}")

        # cleanup_old_workers()

        sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, handle_shutdown_signal)
signal.signal(signal.SIGINT, handle_shutdown_signal)
signal.signal(signal.SIGQUIT, handle_shutdown_signal)


def shared_task(*args, **kwargs):

    """
    Decorator to make a celery's shared_task decorator async-friendly.
    With nest_asyncio applied, we can safely use asyncio.run() even in nested contexts.
    Includes proper signal handling for graceful task termination.
    """

    def decorator(task_func):

        def inner(*a, **k):
            # Check if shutdown was requested
            if _shutdown_requested:
                logger.warning("Task execution cancelled due to shutdown request")
                return None

            try:
                if asyncio.iscoroutinefunction(task_func):
                    return asyncio.run(task_func(*a, **k))
                return task_func(*a, **k)
            except KeyboardInterrupt:
                logger.warning(f"Task {task_func.__name__} interrupted by user")
                raise
            except Exception as e:
                logger.exception(f"Task {task_func.__name__} failed with error: {e}")
                raise

        return _shared_task(*args, **kwargs)(inner)

    return decorator


