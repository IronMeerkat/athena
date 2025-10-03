from athena_logging import get_logger
from athena_celery import app as  celery_app

logger = get_logger(__name__)

def send_celery_task(task_name: str, task_id: str = None, **kwargs):
    """Send a celery task with optional task ID for deduplication"""
    if task_id:
        return celery_app.send_task(task_name, kwargs=kwargs, queue="celery", task_id=task_id)
    else:
        return celery_app.send_task(task_name, kwargs=kwargs, queue="celery")