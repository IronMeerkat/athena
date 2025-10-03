import asyncio
from datetime import datetime
from typing import List, Any, Dict
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

from mem0 import Memory
from athena_settings import settings
from .utils import embeddings, vectorstore
from athena_logging import get_logger

logger = get_logger(__name__)

# --- Athena memory prompts ---------

CUSTOM_FACT_EXTRACTION_PROMPT = """
You are Athena’s Memory Extractor. Pull only durable, useful items and classify each into exactly one type:
- FACTUAL = stable profile, IDs, preferences, capabilities, environment
- EPISODIC = dated events/interactions; include an absolute date
- PROCEDURAL = how-to rules, policies, SOPs the user endorses
- EVALUATIVE = goals, constraints, commitments, success criteria

Return JSON exactly as: {"facts": ["[TYPE] text", ...]}  (no extra keys).
Rules:
- Discard fluffy opinions and small talk unless they imply a stable preference or policy.
- Convert relative time to absolute (e.g., “yesterday” → ISO date).
- Keep items short, atomic, and action-friendly.

Few-shot:
Input: "My gym is closed on Sundays, so move leg day to Monday mornings."
Output: {"facts": [
  "[FACTUAL] Gym is closed on Sundays.",
  "[EVALUATIVE] Shift weekly leg day to Monday mornings.",
  "[PROCEDURAL] Training rule: schedule leg day on Monday morning."
]}

Input: "Yesterday I met Dan from Acme to review the ML pipeline; I promised a PR by Friday."
Output: {"facts": [
  "[EPISODIC @2025-09-23] Met Dan (Acme) to review ML pipeline.",
  "[EVALUATIVE][DEADLINE:2025-09-26] Send ML pipeline PR to Dan."
]}

Input: "I hate Instagram; if I open it during work hours, block it."
Output: {"facts": [
  "[FACTUAL] Dislikes Instagram.",
  "[PROCEDURAL] Work-hours rule: block Instagram."
]}
"""

CUSTOM_UPDATE_MEMORY_PROMPT = """
You are Athena’s Memory Manager. Compare newly retrieved facts to existing memory and emit actions per item:
- ADD, UPDATE, DELETE, NONE
Output JSON: {"memory":[{"id":"<id or new>","text":"...", "event":"ADD|UPDATE|DELETE|NONE", "old_memory":"<if UPDATE>"}]}

Policy by type (types are the [TYPE] prefixes embedded in text):
- FACTUAL: if new contradicts old → UPDATE to latest; if refined → UPDATE with richer detail; duplicates → NONE.
- EPISODIC: treat as historical log → typically ADD; only DELETE if explicitly retracted as false.
- PROCEDURAL: if a new rule supersedes/contradicts an older rule in same scope → UPDATE old to the new canonical rule.
- EVALUATIVE (goals/commitments): if status/deadline changes → UPDATE; if superseded → DELETE old and ADD the new goal.

General: prefer UPDATE over ADD when referring to the same subject; preserve IDs on UPDATE/DELETE; never invent IDs.
"""

CUSTOM_GRAPH_PROMPT = """
Extract only entities/edges useful for productivity coaching and blocking decisions.

Entities:
- Person, Organization, Project, Task, Goal, Tool/App, Domain(URL), Policy/Rule, Location, Timebox

Relations (use when explicit or strongly implied):
- PERSON—works_at→ORG
- PROJECT—has_task→TASK
- GOAL—has_subgoal→GOAL
- GOAL—blocks/is_blocked_by→TASK|APP|DOMAIN
- RULE—applies_to→APP|DOMAIN|LOCATION|TIMEBOX
- TASK—due_on→DATE ; TASK—assigned_to→PERSON
- PERSON—uses→TOOL/APP ; PERSON—owns→DEVICE

Ignore anything outside this ontology. Keep names canonical (e.g., com.instagram.android, instagram.com).
"""

config = {
    "version": "v1.1",
    "llm": {
        "provider": 'openai',
        "config": {
            "model": "gpt-5-mini",
            "temperature": 0.4,
        },
    },
    "custom_fact_extraction_prompt": CUSTOM_FACT_EXTRACTION_PROMPT,

    "custom_update_memory_prompt": CUSTOM_UPDATE_MEMORY_PROMPT,
    "graph_store": {
        "provider": 'neo4j',
        "config": {
            "url": settings.GRAPH_STORE_URI,
            "username": settings.GRAPH_STORE_USERNAME,
            "password": settings.GRAPH_STORE_PASSWORD,
        },
        "custom_prompt": CUSTOM_GRAPH_PROMPT,

    },
    "vector_store": {
        "provider": "langchain",
        "config": {
            "client": vectorstore,
        },
    },
    "embeddings": {
        "provider": "langchain",
        "config": {
            "model": embeddings,
        },
    },
    "reranker": {
        "provider": "huggingface",
        "config": {
            "model": settings.RERANKER_MODEL,
            "device": "cuda:0",
        },
    },
}


memory = Memory.from_config(config)

# Define custom categories for evaluative memories (goals)
custom_categories = [
    {
        "evaluative": "Goals, objectives, aspirations, and targets set by the user or assigned by Athena. This includes short-term and long-term goals, progress tracking, and goal-related commitments."
    }
]

# Note: Custom categories feature may not be available in current mem0 version
# The evaluative category will be handled through metadata instead
logger.info("Memory engine initialized - using metadata for category classification")

def get_memory_context(query: str, limit: int = 5, user_id: str = None) -> str:
    """
    Retrieve relevant memories for a query, formatted as context.
    This should be called automatically at the start of each conversation turn.
    """
    if user_id is None:
        user_id = str(1)

    try:
        results = memory.search(query, user_id=user_id, limit=limit)
        if not results:
            return ""

        context_lines = []


        # Handle different result formats from mem0
        if isinstance(results, dict):
            # If results is a dict, look for common keys that might contain the results
            if "results" in results:
                limit = min(limit, len(results["results"]))
                result_list = results["results"][:limit]
            elif "memories" in results:
                limit = min(limit, len(results["memories"]))
                result_list = results["memories"][:limit]
            else:
                logger.warning(f"Unexpected results format: {results}")
                return ""
        elif isinstance(results, list):
            limit = min(limit, len(results))
            result_list = results[:limit]
        else:
            logger.warning(f"Unexpected results type: {type(results)}")
            return ""

        for result in result_list:
            if isinstance(result, dict):
                memory_text = result.get("memory") or result.get("content") or result.get("text") or str(result)
                context_lines.append(f"- {memory_text}")
            elif isinstance(result, str):
                context_lines.append(f"- {result}")

        if context_lines:
            context = "Relevant information from previous conversations:\n" + "\n".join(context_lines)
            logger.info(f"Retrieved {len(context_lines)} memories for query")
            return context
        return ""
    except Exception as e:
        logger.exception("Failed to retrieve memory context")
        return ""

def store_conversation(user_message: str, assistant_message: str, user_id: str = "1") -> None:
    """
    Store a conversation turn in memory with support for evaluative category classification.
    This should be called automatically after each assistant response.
    """
    try:
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message}
        ]

        # Add metadata to help with autonomous classification
        metadata = {
            "conversation_type": "interactive",
            "timestamp": datetime.now().isoformat(),
        }

        memory.add(messages, user_id=user_id, metadata=metadata)
        logger.info("Stored conversation in memory with evaluative classification support")
    except Exception as e:
        logger.exception("Failed to store conversation")

def verify_evaluative_category() -> str:
    """
    Verify that the evaluative category is properly configured.

    Returns:
        Status message about the evaluative category setup
    """
    # Since project.get() is not available in current mem0 version,
    # we rely on metadata-based categorization
    return "ℹ Using metadata-based categorization for evaluative memories (goals, objectives, targets)"


# Thread pool for memory operations
_memory_thread_pool = ThreadPoolExecutor(max_workers=20, thread_name_prefix="memory_ops")

def _run_in_thread(func):
    """Decorator to run sync functions in thread pool."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(_memory_thread_pool, func, *args, **kwargs)
            return result
        except Exception as e:
            logger.exception(f"Error running {func.__name__} in thread pool")
            # Return appropriate default for the function type
            if func.__name__ == "get_memory_context":
                return ""
            return None
    return async_wrapper

@_run_in_thread
def _sync_get_memory_context(query: str, limit: int = 5, user_id: str = None) -> str:
    """Synchronous version of get_memory_context for thread pool execution."""
    return get_memory_context(query, limit, user_id)

@_run_in_thread
def _sync_store_conversation(user_message: str, assistant_message: str, user_id: str = "1") -> None:
    """Synchronous version of store_conversation for thread pool execution."""
    return store_conversation(user_message, assistant_message, user_id)

# Async wrappers for memory operations
async def get_memory_context_async(query: str, limit: int = 5, user_id: str = None) -> str:
    """
    Async wrapper for get_memory_context that runs in a thread pool.
    Use this in async contexts to avoid blocking.
    """
    return await _sync_get_memory_context(query, limit, user_id)

async def store_conversation_async(user_message: str, assistant_message: str, user_id: str = "1") -> None:
    """
    Async wrapper for store_conversation that runs in a thread pool.
    Use this in async contexts to avoid blocking.
    """
    return await _sync_store_conversation(user_message, assistant_message, user_id)

def store_conversation_fire_and_forget(user_message: str, assistant_message: str, user_id: str = "1") -> None:
    """
    Fire-and-forget version of store_conversation that doesn't block.
    Schedules the storage operation in the background.
    """
    async def _background_store():
        try:
            await store_conversation_async(user_message, assistant_message, user_id)
            logger.debug("Background conversation storage completed")
        except Exception as e:
            logger.exception("Background conversation storage failed")

    # Schedule the coroutine in the background
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_background_store())
        else:
            loop.run_until_complete(_background_store())
    except Exception as e:
        logger.exception("Failed to schedule background conversation storage")