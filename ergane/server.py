import asyncio
import sys
from typing import List, Dict, Any, Optional

from athena_logging import get_logger
from athena_settings import settings
from athena_models import Prompt, PromptRole, db_session
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
import sqlalchemy as sa

logger = get_logger(__name__)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ergane", debug=True)


@mcp.tool()
def get_prompt(key: str, version: Optional[int] = None) -> Dict[str, Any]:
    """Retrieve a prompt by its key. If version not specified, returns the latest version."""
    try:
        with db_session() as session:
            stmt = select(Prompt).where(Prompt.key == key, Prompt.is_active == True)

            if version:
                # Get specific version
                stmt = stmt.where(Prompt.version == version)
                prompt = session.execute(stmt).scalar_one_or_none()
            else:
                # Get latest version
                stmt = stmt.order_by(Prompt.version.desc())
                prompt = session.execute(stmt).first()
                if prompt:
                    prompt = prompt[0]  # Unpack from tuple

            if not prompt:
                version_msg = f" version {version}" if version else " (latest version)"
                raise ValueError(f"Prompt with key '{key}'{version_msg} not found")

            return {
                "id": prompt.id,
                "key": prompt.key,
                "title": prompt.title,
                "content": prompt.content,
                "version": prompt.version,
                "role": prompt.role.value,
                "prompt_metadata": prompt.prompt_metadata,
                "message_config": prompt.message_config
            }
    except Exception as e:
        logger.error(f"Failed to get prompt {key}: {e}")
        raise


@mcp.tool()
def list_prompts(latest_only: bool = True, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """List prompts. If latest_only=True, returns only the latest version of each key."""
    try:
        with db_session() as session:
            if latest_only:
                # Subquery to get the max version for each key
                subq = session.query(
                    Prompt.key,
                    sa.func.max(Prompt.version).label('max_version')
                ).filter(Prompt.is_active == True).group_by(Prompt.key).subquery()

                stmt = select(Prompt).join(
                    subq,
                    and_(
                        Prompt.key == subq.c.key,
                        Prompt.version == subq.c.max_version
                    )
                ).where(Prompt.is_active == True)
            else:
                stmt = select(Prompt).where(Prompt.is_active == True)

            prompts = session.execute(stmt).scalars().all()

            # Apply metadata filtering if specified
            if metadata_filter:
                filtered_prompts = []
                for p in prompts:
                    match = True
                for key, value in metadata_filter.items():
                    if p.prompt_metadata.get(key) != value:
                            match = False
                            break
                    if match:
                        filtered_prompts.append(p)
                prompts = filtered_prompts

            return [
                {
                    "id": p.id,
                    "key": p.key,
                    "title": p.title,
                    "version": p.version,
                    "role": p.role.value,
                    "metadata": p.metadata
                }
                for p in prompts
            ]
    except Exception as e:
        logger.error(f"Failed to list prompts: {e}")
        raise


@mcp.tool()
def get_topic_prompts() -> Dict[str, Dict[str, Any]]:
    """Get all topic-specific prompts as a dictionary (similar to TOPIC_PROMPT_DICT)."""
    try:
        with db_session() as session:
            # Get latest versions of prompts with prompt_type = topic_specific
            subq = session.query(
                Prompt.key,
                sa.func.max(Prompt.version).label('max_version')
            ).filter(Prompt.is_active == True).group_by(Prompt.key).subquery()

            stmt = select(Prompt).join(
                subq,
                and_(
                    Prompt.key == subq.c.key,
                    Prompt.version == subq.c.max_version
                )
            ).where(Prompt.is_active == True)

            prompts = session.execute(stmt).scalars().all()

            result = {}
            for prompt in prompts:
                # Check if this is a topic-specific prompt
                if prompt.prompt_metadata.get("prompt_type") == "topic_specific":
                    topic_key = prompt.prompt_metadata.get("topic_key")
                    if topic_key:
                        result[topic_key] = {
                            "id": prompt.id,
                            "key": prompt.key,
                            "title": prompt.title,
                            "content": prompt.content,
                            "version": prompt.version,
                            "role": prompt.role.value,
                            "prompt_metadata": prompt.prompt_metadata,
                            "message_config": prompt.message_config
                        }

            return result
    except Exception as e:
        logger.error(f"Failed to get topic prompts: {e}")
        raise


@mcp.tool()
def create_prompt(
    key: str,
    title: str,
    content: str,
    role: str,
    version: Optional[int] = None,
    prompt_metadata: Optional[Dict[str, Any]] = None,
    message_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a new prompt. If version not specified, creates the next version."""
    try:
        with db_session() as session:
            if version is None:
                # Find the highest existing version for this key
                max_version = session.query(sa.func.max(Prompt.version)).filter(Prompt.key == key).scalar()
                version = (max_version or 0) + 1

            prompt = Prompt(
                key=key,
                title=title,
                content=content,
                version=version,
                role=PromptRole(role),
                prompt_metadata=prompt_metadata or {},
                message_config=message_config or {"skip_storage": True}
            )

            session.add(prompt)
            session.commit()

            logger.info(f"Created prompt with key: {key}, version: {version}")

            return {
                "id": prompt.id,
                "key": prompt.key,
                "title": prompt.title,
                "version": prompt.version,
                "role": prompt.role.value,
                "created": True
            }
    except Exception as e:
        logger.error(f"Failed to create prompt {key}: {e}")
        raise


@mcp.tool()
def update_prompt(
    key: str,
    version: Optional[int] = None,
    title: Optional[str] = None,
    content: Optional[str] = None,
    role: Optional[str] = None,
    prompt_metadata: Optional[Dict[str, Any]] = None,
    message_config: Optional[Dict[str, Any]] = None,
    is_active: Optional[bool] = None,
    create_new_version: bool = True
) -> Dict[str, Any]:
    """Update a prompt. If create_new_version=True, creates a new version. Otherwise updates the specified version in place."""
    try:
        with db_session() as session:
            if version is None:
                # Get the latest version
                stmt = select(Prompt).where(Prompt.key == key, Prompt.is_active == True).order_by(Prompt.version.desc())
                existing_prompt = session.execute(stmt).first()
                if existing_prompt:
                    existing_prompt = existing_prompt[0]
                else:
                    raise ValueError(f"No active prompt found with key '{key}'")
            else:
                # Get specific version
                stmt = select(Prompt).where(Prompt.key == key, Prompt.version == version)
                existing_prompt = session.execute(stmt).scalar_one_or_none()
                if not existing_prompt:
                    raise ValueError(f"Prompt with key '{key}' version {version} not found")

            if create_new_version:
                # Create new version with updates
                max_version = session.query(sa.func.max(Prompt.version)).filter(Prompt.key == key).scalar()
                new_version = (max_version or 0) + 1

                new_prompt = Prompt(
                    key=key,
                    title=title if title is not None else existing_prompt.title,
                    content=content if content is not None else existing_prompt.content,
                    version=new_version,
                    role=PromptRole(role) if role is not None else existing_prompt.role,
                    prompt_metadata=prompt_metadata if prompt_metadata is not None else existing_prompt.prompt_metadata,
                    message_config=message_config if message_config is not None else existing_prompt.message_config,
                    is_active=is_active if is_active is not None else existing_prompt.is_active
                )

                session.add(new_prompt)
                session.commit()

                logger.info(f"Created new version {new_version} of prompt: {key}")

                return {
                    "id": new_prompt.id,
                    "key": new_prompt.key,
                    "version": new_prompt.version,
                    "created_new_version": True
                }
            else:
                # Update existing version in place
                if title is not None:
                    existing_prompt.title = title
                if content is not None:
                    existing_prompt.content = content
                if role is not None:
                    existing_prompt.role = PromptRole(role)
                if prompt_metadata is not None:
                    existing_prompt.prompt_metadata = prompt_metadata
                if message_config is not None:
                    existing_prompt.message_config = message_config
                if is_active is not None:
                    existing_prompt.is_active = is_active

                session.commit()

                logger.info(f"Updated prompt {key} version {existing_prompt.version} in place")

                return {
                    "id": existing_prompt.id,
                    "key": existing_prompt.key,
                    "version": existing_prompt.version,
                    "updated_in_place": True
                }

    except Exception as e:
        logger.error(f"Failed to update prompt {key}: {e}")
        raise


@mcp.tool()
def get_available_roles() -> List[str]:
    """Get list of available prompt roles."""
    return [role.value for role in PromptRole]


asyncio.run(mcp.run_stdio_async())

