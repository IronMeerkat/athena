"""
Agentless restart utilities for handling /start commands without going through full agent pipeline.
"""

import asyncio
from typing import Optional, Dict, Any
from langgraph.graph.state import RunnableConfig
from langgraph.checkpoint.redis import AsyncRedisSaver
from langchain_core.messages import BaseMessage

from utils import checkpointer, archive_thread, BaseState
from athena_logging import get_logger

logger = get_logger(__name__)


async def retrieve_existing_state(session_id: str, namespace: str = "global") -> Optional[BaseState]:
    """
    Retrieve the existing state for a session from the checkpointer.

    Args:
        session_id: The session/thread ID
        namespace: The checkpoint namespace (default: "global")

    Returns:
        BaseState if found, None otherwise
    """
    try:
        config = RunnableConfig(
            configurable={
                "thread_id": str(session_id),
                "checkpoint_ns": namespace
            }
        )

        # Try to get the latest checkpoint tuple for this thread
        checkpoint_tuple = await checkpointer.aget_tuple(config)

        if checkpoint_tuple and checkpoint_tuple.checkpoint:
            # Extract the state from the checkpoint
            checkpoint_data = checkpoint_tuple.checkpoint

            # The state should be in the 'channel_values' of the checkpoint
            if 'channel_values' in checkpoint_data:
                state_data = checkpoint_data['channel_values']

                # Create a BaseState from the checkpoint data
                state = BaseState(**state_data)
                state.session_id = int(session_id)
                return state

        return None

    except Exception as e:
        logger.warning(f"Failed to retrieve existing state for session {session_id}: {e}")
        return None


async def agentless_start(session_id: str, namespace: str = "global") -> bool:
    """
    Handle an agentless /start command by:
    1. Retrieving existing messages from checkpointer
    2. Archiving them using archive_thread
    3. Clearing the checkpointer state
    4. Returning True

    Args:
        session_id: The session/thread ID to restart
        namespace: The checkpoint namespace (default: "global")

    Returns:
        status (bool)
    """
    try:
        logger.debug(f"Starting agentless restart for session {session_id}")

        # Step 1: Retrieve existing state
        existing_state = await retrieve_existing_state(session_id, namespace)

        # Step 2: Archive messages if state exists and has interesting messages
        if existing_state and existing_state.interesting_messages:
            logger.info(f"Archiving {len(existing_state.interesting_messages)} messages for session {session_id}")
            await archive_thread(existing_state, namespace=namespace)
        else:
            logger.info(f"No messages to archive for session {session_id}")

        # Step 3: Clear the checkpointer state
        await checkpointer.adelete_thread(str(session_id))
        logger.info(f"Cleared checkpointer state for session {session_id}")

        # Step 4: Return True
        return True

    except Exception as e:
        logger.exception(f"Failed to handle agentless start for session {session_id}")
        # Fall back to returning False even if archiving failed
        return False
