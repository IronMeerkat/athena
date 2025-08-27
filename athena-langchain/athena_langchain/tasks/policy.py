from __future__ import annotations

from typing import Any, Dict, List

from celery import shared_task

from ..config import Settings
from ..policies.schedule import (
    save_schedule,
    load_schedule,
    get_current_strictness,
    get_current_goal,
)


@shared_task(name="policy.schedule_get")
def schedule_get(user_key: str) -> List[Dict[str, Any]]:
    settings = Settings()
    return load_schedule(settings, session_id=user_key)


@shared_task(name="policy.schedule_set")
def schedule_set(user_key: str, schedule: List[Dict[str, Any]]) -> bool:
    settings = Settings()
    save_schedule(settings, schedule, session_id=user_key)
    return True


@shared_task(name="policy.strictness_get")
def strictness_get(user_key: str) -> int:
    settings = Settings()
    return get_current_strictness(settings, session_id=user_key)


@shared_task(name="policy.goal_get")
def goal_get(user_key: str) -> str:
    settings = Settings()
    return get_current_goal(settings, session_id=user_key)


