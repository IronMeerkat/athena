from __future__ import annotations

from typing import List, Optional
from datetime import datetime
import json

from athena_logging import get_logger
from langchain_core.tools import tool

from utils.memory_engine import memory
from utils.emotional_engine import Commitment, Boundary, InterpersonalEpisode, CommitmentStatus, Target

logger = get_logger(__name__)

@tool("search_commitments")
def search_commitments(status: str = "active", party: str = "", user_id: str = "1") -> str:
    """
    Search for commitments by status and party.

    Args:
        status: Commitment status ("active", "paused", "completed", "broken", "all")
        party: Filter by party ("user", "athena", or empty for all)
        user_id: User identifier

    Returns:
        List of matching commitments
    """
    try:
        query = "COMMITMENT"
        if status != "all":
            query += f" status:{status}"
        if party:
            query += f" party:{party}"

        results = memory.search(query, user_id=user_id, limit=20)

        if not results:
            return "No commitments found."

        commitment_texts = []
        for i, result in enumerate(results, 1):
            if isinstance(result, dict):
                content = result.get("memory") or result.get("content") or str(result)
                if "COMMITMENT:" in content:
                    try:
                        commitment_json = content.split("COMMITMENT:", 1)[1].strip()
                        commitment = json.loads(commitment_json)
                        if (status == "all" or commitment.get("status") == status) and \
                           (not party or commitment.get("party") == party):
                            commitment_texts.append(
                                f"{i}. [{commitment['id']}] {commitment['party']}: {commitment['promise']} "
                                f"(Status: {commitment['status']}, KPI: {commitment['kpi']})"
                            )
                    except json.JSONDecodeError:
                        continue

        if not commitment_texts:
            return f"No {status} commitments found for {party or 'any party'}."

        return f"Commitments ({status}):\n" + "\n".join(commitment_texts)
    except Exception as e:
        logger.exception("Failed to search commitments")
        return f"Failed to search commitments: {str(e)}"

@tool("update_commitment_status")
def update_commitment_status(commitment_id: str, new_status: str, user_id: str = "1") -> str:
    """
    Update the status of a commitment.

    Args:
        commitment_id: ID of the commitment to update
        new_status: New status ("active", "paused", "completed", "broken")
        user_id: User identifier

    Returns:
        Confirmation message
    """
    try:
        # Find the commitment
        results = memory.search(f"COMMITMENT {commitment_id}", user_id=user_id, limit=5)

        for result in results:
            if isinstance(result, dict):
                content = result.get("memory") or result.get("content") or str(result)
                if "COMMITMENT:" in content and commitment_id in content:
                    try:
                        commitment_json = content.split("COMMITMENT:", 1)[1].strip()
                        commitment = json.loads(commitment_json)
                        commitment["status"] = new_status

                        new_content = f"COMMITMENT: {json.dumps(commitment)}"
                        memory_id = result.get("id") or result.get("_id")

                        if memory_id:
                            memory.update(memory_id, new_content)
                            logger.info(f"Updated commitment {commitment_id} status to {new_status}")
                            return f"Commitment {commitment_id} status updated to {new_status}"

                    except json.JSONDecodeError:
                        continue

        return f"Commitment {commitment_id} not found"
    except Exception as e:
        logger.exception("Failed to update commitment status")
        return f"Failed to update commitment: {str(e)}"

@tool("add_boundary")
def add_boundary(description: str, context: str = "general", user_id: str = "1") -> str:
    """
    Add a boundary rule for what Athena will/won't do.

    Args:
        description: What the boundary is (e.g. "won't schedule doom-scroll during strict mode")
        context: Context where this applies (e.g. "strict_mode", "focus_sessions")
        user_id: User identifier

    Returns:
        Boundary ID for tracking
    """
    try:
        boundary_id = f"boundary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        boundary_data = {
            "id": boundary_id,
            "description": description,
            "context": context,
            "active": True,
            "created_at": datetime.now().isoformat()
        }

        messages = [
            {"role": "system", "content": f"BOUNDARY: {json.dumps(boundary_data)}"}
        ]

        metadata = {
            "category": "contracts.boundaries",
            "boundary_id": boundary_id,
            "context": context
        }

        memory.add(messages, user_id=user_id, metadata=metadata)
        logger.info(f"Added boundary {boundary_id}")
        return f"Boundary recorded: {boundary_id} - {description}"
    except Exception as e:
        logger.exception("Failed to add boundary")
        return f"Failed to add boundary: {str(e)}"

@tool("log_interpersonal_episode")
def log_interpersonal_episode(
    target: str,  # "user", "self", or "external"
    intensity: float,
    valence: float,
    arousal: float,
    control: float,
    uncertainty: float,
    narrative: str,
    commitment_ids: List[str] = None,
    user_id: str = "1"
) -> str:
    """
    Log an interpersonal episode with emotional context for future attribution.

    Args:
        target: Who is responsible ("user", "self", "external")
        intensity: Intensity level (0.0 to 1.0)
        valence: Emotional valence (-1.0 to 1.0)
        arousal: Arousal level (0.0 to 1.0)
        control: Control level (0.0 to 1.0)
        uncertainty: Uncertainty level (0.0 to 1.0)
        narrative: Brief description of what happened
        commitment_ids: Related commitment IDs
        user_id: User identifier

    Returns:
        Episode ID for tracking
    """
    try:
        episode_id = f"episode_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        episode_data = {
            "id": episode_id,
            "target": target,
            "intensity": intensity,
            "valence": valence,
            "arousal": arousal,
            "control": control,
            "uncertainty": uncertainty,
            "narrative": narrative,
            "commitment_ids": commitment_ids or [],
            "timestamp": datetime.now().isoformat(),
            "resolved": False
        }

        messages = [
            {"role": "system", "content": f"EPISODE: {json.dumps(episode_data)}"}
        ]

        metadata = {
            "category": "episodes.interpersonal",
            "episode_id": episode_id,
            "target": target,
            "intensity": intensity
        }

        memory.add(messages, user_id=user_id, metadata=metadata)
        logger.info(f"Logged interpersonal episode {episode_id}")
        return f"Episode logged: {episode_id} - {narrative}"
    except Exception as e:
        logger.exception("Failed to log interpersonal episode")
        return f"Failed to log episode: {str(e)}"

@tool("search_episodes")
def search_episodes(target: str = "", resolved: str = "false", limit: int = 10, user_id: str = "1") -> str:
    """
    Search for interpersonal episodes.

    Args:
        target: Filter by target ("user", "self", "external", or empty for all)
        resolved: Filter by resolution status ("true", "false", or "all")
        limit: Maximum results to return
        user_id: User identifier

    Returns:
        List of matching episodes
    """
    try:
        query = "EPISODE"
        if target:
            query += f" target:{target}"

        results = memory.search(query, user_id=user_id, limit=limit)

        if not results:
            return "No episodes found."

        episode_texts = []
        for i, result in enumerate(results, 1):
            if isinstance(result, dict):
                content = result.get("memory") or result.get("content") or str(result)
                if "EPISODE:" in content:
                    try:
                        episode_json = content.split("EPISODE:", 1)[1].strip()
                        episode = json.loads(episode_json)

                        # Apply filters
                        if target and episode.get("target") != target:
                            continue
                        if resolved != "all":
                            episode_resolved = episode.get("resolved", False)
                            if (resolved == "true") != episode_resolved:
                                continue

                        episode_texts.append(
                            f"{i}. [{episode['id']}] Target: {episode['target']}, "
                            f"Intensity: {episode['intensity']:.2f}, "
                            f"V/A/C/U: {episode['valence']:.2f}/{episode['arousal']:.2f}/"
                            f"{episode['control']:.2f}/{episode['uncertainty']:.2f}, "
                            f"Narrative: {episode['narrative']}"
                        )
                    except json.JSONDecodeError:
                        continue

        if not episode_texts:
            return f"No episodes found matching criteria."

        return f"Interpersonal Episodes:\n" + "\n".join(episode_texts)
    except Exception as e:
        logger.exception("Failed to search episodes")
        return f"Failed to search episodes: {str(e)}"

@tool("resolve_episode")
def resolve_episode(episode_id: str, user_id: str = "1") -> str:
    """
    Mark an interpersonal episode as resolved.

    Args:
        episode_id: ID of the episode to resolve
        user_id: User identifier

    Returns:
        Confirmation message
    """
    try:
        results = memory.search(f"EPISODE {episode_id}", user_id=user_id, limit=5)

        for result in results:
            if isinstance(result, dict):
                content = result.get("memory") or result.get("content") or str(result)
                if "EPISODE:" in content and episode_id in content:
                    try:
                        episode_json = content.split("EPISODE:", 1)[1].strip()
                        episode = json.loads(episode_json)
                        episode["resolved"] = True

                        new_content = f"EPISODE: {json.dumps(episode)}"
                        memory_id = result.get("id") or result.get("_id")

                        if memory_id:
                            memory.update(memory_id, new_content)
                            logger.info(f"Resolved episode {episode_id}")
                            return f"Episode {episode_id} marked as resolved"

                    except json.JSONDecodeError:
                        continue

        return f"Episode {episode_id} not found"
    except Exception as e:
        logger.exception("Failed to resolve episode")
        return f"Failed to resolve episode: {str(e)}"

@tool("get_current_mood")
def get_current_mood(user_id: str = "1") -> str:
    """
    Get Athena's current mood and emotional state.
    Returns a compact description with emoji, label, and raw values.
    """
    try:
        from polymetis.utils.mood_redis import get_current_mood as get_mood_redis

        mood = get_mood_redis(user_id)
        if not mood:
            return "Current mood unavailable (no recent emotional state updates)"

        # Calculate time since last update
        from datetime import datetime, timezone
        try:
            ts = datetime.fromisoformat(mood.ts.replace('Z', '+00:00'))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            minutes_ago = int((now - ts).total_seconds() / 60)
            time_str = f" ({minutes_ago}min ago)" if minutes_ago > 0 else ""
        except Exception:
            time_str = ""

        return (f"Current mood: {mood.format_status()}\n"
                f"Color: {mood.color_hex}{time_str}\n"
                f"Attribution: {mood.T.value} (intensity: {mood.I:.2f})")
    except Exception as e:
        logger.exception("Failed to get current mood")
        return f"Failed to get current mood: {str(e)}"

# Export emotional memory tools
emotional_memory_tools = [
    search_commitments, update_commitment_status, add_boundary,
    log_interpersonal_episode, search_episodes, resolve_episode,
    get_current_mood
]
