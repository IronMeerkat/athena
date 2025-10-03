from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from athena_logging import get_logger
from langchain_core.tools import tool

from utils.memory_engine import memory
from utils.emotional_engine import Commitment, Boundary, InterpersonalEpisode, CommitmentStatus, Target

logger = get_logger(__name__)

@tool("search_memories")
def search_memories(query: str, limit: int = 3, user_id: str = None) -> str:
    """
    Search through stored memories to find specific information.
    Use this when you need to find particular details from past conversations
    that weren't automatically retrieved in the context.

    Args:
        query: What to search for in memories
        limit: Maximum number of results to return (default: 3)
        user_id: User identifier for memory search (defaults to TELEGRAM_USER_ID)

    Returns:
        Relevant memories found
    """
    from athena_settings import settings

    if user_id is None:
        user_id = str(1)

    try:
        results = memory.search(query, user_id=user_id, limit=limit)

        if not results:
            return "No relevant memories found for this query."

        memory_texts = []
        for i, result in enumerate(results[:limit], 1):
            if isinstance(result, dict):
                memory_text = result.get("memory") or result.get("content") or result.get("text") or str(result)
                memory_id = result.get("id") or result.get("_id") or f"mem_{i}"
                memory_texts.append(f"{i}. [{memory_id}] {memory_text}")
            else:
                memory_texts.append(f"{i}. {str(result)}")

        logger.info(f"Found {len(memory_texts)} memories for query: {query}")
        return "\n".join(memory_texts)
    except Exception as e:
        logger.exception("Failed to search memories")
        return f"Failed to search memories: {str(e)}"

@tool("update_memory")
def update_memory(memory_id: str, new_content: str) -> str:
    """
    Update an existing memory with corrected or updated information.
    Use this when the user corrects previous information or provides updates.

    Args:
        memory_id: ID of the memory to update (from search results)
        new_content: New content to replace the old memory

    Returns:
        Confirmation message
    """
    try:
        # Try different update signatures that Mem0 might support
        try:
            memory.update(memory_id, new_content)
        except TypeError:
            memory.update(memory_id, {"content": new_content})

        logger.info(f"Updated memory {memory_id}")
        return f"Memory {memory_id} updated successfully."
    except Exception as e:
        logger.exception("Failed to update memory")
        return f"Failed to update memory: {str(e)}"

@tool("delete_memory")
def delete_memory(memory_id: str) -> str:
    """
    Delete a memory that is no longer relevant or accurate.
    Use this to remove outdated, incorrect, or sensitive information.

    Args:
        memory_id: ID of the memory to delete (from search results)

    Returns:
        Confirmation message
    """
    try:
        memory.delete(memory_id)
        logger.info(f"Deleted memory {memory_id}")
        return f"Memory {memory_id} deleted successfully."
    except Exception as e:
        logger.exception("Failed to delete memory")
        return f"Failed to delete memory: {str(e)}"

@tool("search_goals")
def search_goals(query: str = "", limit: int = 5, user_id: str = "1") -> str:
    """
    Search specifically for goal-related memories (evaluative category).
    Use this to find goals, objectives, and targets.

    Args:
        query: Specific goal to search for (optional - searches all goals if empty)
        limit: Maximum number of results to return
        user_id: User identifier for memory search

    Returns:
        Goal-related memories found
    """
    try:
        # Search with goal-related terms to find evaluative memories
        search_query = f"goals objectives targets plans aims {query}".strip()
        results = memory.search(search_query, user_id=user_id, limit=limit)

        if not results:
            return "No goals found."

        goal_texts = []
        for i, result in enumerate(results[:limit], 1):
            if isinstance(result, dict):
                memory_text = result.get("memory") or result.get("content") or str(result)
                memory_id = result.get("id") or f"goal_{i}"
                category = result.get("category", "unknown")

                # Prioritize evaluative category or filter for goal-related content
                if (category == "evaluative" or
                    any(keyword in memory_text.lower() for keyword in
                        ['goal', 'objective', 'target', 'aim', 'want to', 'plan to', 'will complete', 'assigned'])):
                    goal_texts.append(f"{i}. [{memory_id}] {memory_text}")

        if not goal_texts:
            return "No goal-related memories found."

        return f"Current Goals:\n" + "\n".join(goal_texts)
    except Exception as e:
        logger.exception("Failed to search goals")
        return f"Failed to search goals: {str(e)}"

@tool("add_goal_memory")
def add_goal_memory(goal_description: str, source: str = "user", user_id: str = "1") -> str:
    """
    Explicitly add a goal to memory with evaluative category metadata.

    Args:
        goal_description: The goal or objective to remember
        source: Who set the goal - "user" or "athena"
        user_id: User identifier for memory storage

    Returns:
        Confirmation message
    """
    try:
        messages = [
            {"role": "user" if source == "user" else "assistant",
             "content": f"Goal: {goal_description}"}
        ]

        metadata = {
            "category": "evaluative",
            "goal_source": source,
            "goal_status": "active",
            "timestamp": datetime.now().isoformat()
        }

        memory.add(messages, user_id=user_id, metadata=metadata)
        logger.info(f"Added goal memory from {source}: {goal_description}")
        return f"Goal recorded: {goal_description}"
    except Exception as e:
        logger.exception("Failed to add goal memory")
        return f"Failed to add goal: {str(e)}"

@tool("get_memory_categories")
def get_memory_categories(user_id: str = "1") -> str:
    """
    Get information about available memory categories including the evaluative category.

    Args:
        user_id: User identifier

    Returns:
        Available memory categories
    """
    # Since project.get() is not available in current mem0 version,
    # we use metadata-based categorization
    return "Available categories (metadata-based): factual, episodic, procedural, evaluative (goals), contracts.commitments"

@tool("add_commitment")
def add_commitment(
    party: str,  # "user" or "athena"
    goal_id: str,
    promise: str,
    kpi_name: str,
    kpi_value: float,
    due: str = "rolling",
    misses_before_nudge: int = 1,
    misses_before_pushback: int = 3,
    user_id: str = "1"
) -> str:
    """
    Add a new commitment to memory for accountability tracking.
    """
    try:
        commitment_id = f"commitment_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{party}"

        commitment_data = {
            "id": commitment_id,
            "party": party,
            "goal_id": goal_id,
            "promise": promise,
            "kpi": {kpi_name: kpi_value},
            "due": due,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "grace": {
                "misses_before_nudge": misses_before_nudge,
                "misses_before_pushback": misses_before_pushback
            }
        }

        messages = [
            {"role": "system", "content": f"COMMITMENT: {json.dumps(commitment_data)}"}
        ]

        metadata = {
            "category": "contracts.commitments",
            "commitment_id": commitment_id,
            "party": party,
            "status": "active"
        }

        memory.add(messages, user_id=user_id, metadata=metadata)
        logger.info(f"Added commitment {commitment_id} for {party}")
        return f"Commitment recorded: {commitment_id} - {party} promises '{promise}'"
    except Exception as e:
        logger.exception("Failed to add commitment")
        return f"Failed to add commitment: {str(e)}"

# Export memory tools with goal-specific functionality and commitment tracking
memory_tools = [search_memories, update_memory, delete_memory, search_goals, add_goal_memory, get_memory_categories, add_commitment]