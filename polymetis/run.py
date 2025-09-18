from athena_celery import app as celery_app
from celery.schedules import crontab
from celery import Celery


# Import the task modules to ensure they're registered
import polymetis.agents.telegram
import polymetis.agents.self_starter

from polymetis.agents.self_starter import self_starter_agent_task

# Configure autodiscovery for polymetis tasks
celery_app.autodiscover_tasks([
    'polymetis.agents.telegram',
    'polymetis.agents.self_starter',
])


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    sender.add_periodic_task(
        crontab(hour=9, minute=0),
        self_starter_agent_task.s(),
    )