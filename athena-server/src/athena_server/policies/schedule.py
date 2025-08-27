from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis

from athena_server.config import Settings  # type: ignore[import-error]


SCHEDULE_KEY_PREFIX = "athena:schedule:"


@dataclass
class TimeBlock:
    start_minutes: int
    end_minutes: int
    strictness: int  # 1..10
    days: Optional[List[int]] = None  # 0=Mon .. 6=Sun; None means all days


def _key(session_id: Optional[str]) -> str:
    sid = session_id or "default"
    return f"{SCHEDULE_KEY_PREFIX}{sid}"


def _redis(settings: Settings) -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url)


def save_schedule(
    settings: Settings,
    schedule: List[Dict[str, Any]],
    *,
    session_id: Optional[str] = None,
) -> None:
    client = _redis(settings)
    client.set(_key(session_id), json.dumps(schedule))


def load_schedule(
    settings: Settings,
    *,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _redis(settings)
    raw = client.get(_key(session_id))
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def get_current_strictness(
    settings: Settings,
    *,
    session_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> int:
    blocks = load_schedule(settings, session_id=session_id)
    if not blocks:
        return 5  # neutral default
    dt = now or datetime.now()
    # Python weekday: Monday=0 .. Sunday=6
    weekday = dt.weekday()
    minutes = dt.hour * 60 + dt.minute
    best: Optional[int] = None
    # If multiple overlapping blocks, pick the max strictness
    for b in blocks:
        start = int(b.get("start_minutes", 0))
        end = int(b.get("end_minutes", 0))
        strict = int(b.get("strictness", 5))
        days = b.get("days")
        if days is not None and isinstance(days, list):
            if weekday not in [int(d) for d in days]:
                continue
        # handle wrap-around blocks spanning midnight
        in_block = False
        if start <= end:
            in_block = minutes >= start and minutes <= end
        else:
            in_block = minutes >= start or minutes <= end
        if in_block:
            if best is None or strict > best:
                best = strict
    return int(best) if best is not None else 5


def get_current_goal(
    settings: Settings,
    *,
    session_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> str:
    """Return the goal string for the current time block, if any.

    Selection rule: among all matching time blocks, choose the most specific
    block (smallest duration). If there is a tie, prefer the later-defined
    block. Strictness is NOT used to select the goal.
    """
    blocks = load_schedule(settings, session_id=session_id)
    if not blocks:
        return ""
    dt = now or datetime.now()
    weekday = dt.weekday()
    minutes = dt.hour * 60 + dt.minute
    best_idx = -1
    best_duration = None  # type: Optional[int]
    best_goal = ""
    for idx, b in enumerate(blocks):
        start = int(b.get("start_minutes", 0))
        end = int(b.get("end_minutes", 0))
        days = b.get("days")
        if days is not None and isinstance(days, list):
            if weekday not in [int(d) for d in days]:
                continue
        if start <= end:
            in_block = minutes >= start and minutes <= end
            duration = end - start
        else:
            in_block = minutes >= start or minutes <= end
            duration = (1440 - start) + end
        if not in_block:
            continue
        if best_duration is None or duration < best_duration or (
            duration == best_duration and idx > best_idx
        ):
            best_duration = duration
            best_idx = idx
            best_goal = str(b.get("goal", ""))
    return best_goal
