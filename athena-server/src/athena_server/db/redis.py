from __future__ import annotations

import redis

from athena_server.config import Settings


def get_redis_client(settings: Settings) -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)
