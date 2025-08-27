from __future__ import annotations

from typing import Callable

from langchain_community.chat_message_histories import RedisChatMessageHistory

from athena_langchain.config import Settings


def get_session_history_factory(settings: Settings) -> Callable[[str], RedisChatMessageHistory]:
    def _factory(session_id: str) -> RedisChatMessageHistory:
        return RedisChatMessageHistory(url=settings.redis_url, session_id=session_id)

    return _factory


