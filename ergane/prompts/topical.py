from typing import List

from langchain_core.messages import BaseMessage
from athena_models import Prompt, PromptRole, db_session
from sqlalchemy import select


async def get_available_topics() -> List[str]:
    async with db_session() as session:
        stmt = select(Prompt).where(Prompt.role == PromptRole.SYSTEM,
                    Prompt.prompt_metadata.get("prompt_type") == "topic")
        prompts = await session.execute(stmt)
        return [prompt.key for prompt in prompts.scalars().all()]

async def get_topic_prompts(topics: List[str]) -> List[BaseMessage]:
    async with db_session() as session:
        stmt = select(Prompt).where(Prompt.role == PromptRole.SYSTEM,
                    Prompt.prompt_metadata.get("prompt_type") == "topic",
                    Prompt.prompt_metadata.get("topic_key").in_(topics))
        prompts = await session.execute(stmt)
        return [prompt.as_message for prompt in prompts.scalars().all()]