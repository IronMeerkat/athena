from athena_logging import get_logger
from athena_celery import app as  celery_app

logger = get_logger(__name__)

def send_celery_task(task_name: str, **kwargs):
    return celery_app.send_task(task_name, kwargs=kwargs, queue="celery")