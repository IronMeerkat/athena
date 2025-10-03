"""
Enhanced affect loop with emotional attribution and commitment tracking
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json

from athena_logging import get_logger

from .emotional_engine import (
    EmotionalState, Goal, Commitment, InterpersonalEpisode,
    appraise, map_emotional_state_to_style, generate_tone_templates,
    should_escalate_intensity,
    Target, ResponseStyle, compute_commitment_signals, attribute_responsibility
)
from .memory_engine import memory
from .mood_redis import set_current_mood

logger = get_logger(__name__)

class AffectLoop:
    """Enhanced affect loop with emotional attribution and commitment tracking"""

    def __init__(self, user_id: str = "1"):
        self.user_id = user_id
        self.emotional_state = EmotionalState()  # Initialize with defaults
        self._strict_sessions_today = 0
        self._last_session_time = None

    def get_commitments(self) -> List[Commitment]:
        """Retrieve active commitments from memory"""
        try:
            results = memory.search("COMMITMENT status:active", user_id=self.user_id, limit=50)
            commitments = []

            for result in results:
                if isinstance(result, dict):
                    content = result.get("memory") or result.get("content", "")
                    if "COMMITMENT:" in content:
                        try:
                            commitment_json = content.split("COMMITMENT:", 1)[1].strip()
                            commitment_data = json.loads(commitment_json)
                            commitment = Commitment(**commitment_data)
                            commitments.append(commitment)
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(f"Failed to parse commitment: {e}")
                            continue

            return commitments
        except Exception as e:
            logger.exception("Failed to get commitments")
            return []

    def get_recent_episodes(self, lookback_days: int = 7) -> List[InterpersonalEpisode]:
        """Retrieve recent interpersonal episodes from memory"""
        try:
            results = memory.search("EPISODE", user_id=self.user_id, limit=100)
            episodes = []

            for result in results:
                if isinstance(result, dict):
                    content = result.get("memory") or result.get("content", "")
                    if "EPISODE:" in content:
                        try:
                            episode_json = content.split("EPISODE:", 1)[1].strip()
                            episode_data = json.loads(episode_json)
                            # Convert timestamp string back to datetime
                            episode_data["timestamp"] = datetime.fromisoformat(episode_data["timestamp"])
                            episode = InterpersonalEpisode(**episode_data)

                            # Filter by lookback period
                            if (datetime.now() - episode.timestamp).days <= lookback_days:
                                episodes.append(episode)
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(f"Failed to parse episode: {e}")
                            continue

            return sorted(episodes, key=lambda x: x.timestamp, reverse=True)
        except Exception as e:
            logger.exception("Failed to get episodes")
            return []

    def update_emotional_state(self, goals: List[Goal]) -> EmotionalState:
        """Update emotional state with goals and commitment context"""
        commitments = self.get_commitments()
        episodes = self.get_recent_episodes()

        # Update emotional state using enhanced appraisal
        self.emotional_state = appraise(
            goals=goals,
            state=self.emotional_state,
            commitments=commitments,
            episodes=episodes
        )

        logger.info(f"Updated emotional state: V={self.emotional_state.V:.2f}, "
                   f"A={self.emotional_state.A:.2f}, C={self.emotional_state.C:.2f}, "
                   f"U={self.emotional_state.U:.2f}, T={self.emotional_state.T}, "
                   f"I={self.emotional_state.I:.2f}")

        # Store mood snapshot in Redis for fast access
        set_current_mood(self.emotional_state, user_id=self.user_id)

        return self.emotional_state

    def get_response_style(self) -> ResponseStyle:
        """Get response style based on current emotional state"""
        return map_emotional_state_to_style(self.emotional_state)

    def generate_response_template(self, context: Dict[str, str] = None) -> str:
        """Generate appropriate response template based on emotional state"""
        style = self.get_response_style()
        return generate_tone_templates(style, context or {})

    def should_escalate(self) -> bool:
        """Check if emotional response should escalate"""
        episodes = self.get_recent_episodes()
        return should_escalate_intensity(self.emotional_state, episodes)

    def log_interaction_episode(self,
                               narrative: str,
                               commitment_ids: List[str] = None,
                               resolved: bool = False) -> str:
        """Log a new interpersonal episode"""
        try:
            episode_id = f"episode_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            episode_data = {
                "id": episode_id,
                "target": self.emotional_state.T.value,
                "intensity": self.emotional_state.I,
                "valence": self.emotional_state.V,
                "arousal": self.emotional_state.A,
                "control": self.emotional_state.C,
                "uncertainty": self.emotional_state.U,
                "narrative": narrative,
                "commitment_ids": commitment_ids or [],
                "timestamp": datetime.now().isoformat(),
                "resolved": resolved
            }

            messages = [
                {"role": "system", "content": f"EPISODE: {json.dumps(episode_data)}"}
            ]

            metadata = {
                "category": "episodes.interpersonal",
                "episode_id": episode_id,
                "target": self.emotional_state.T.value,
                "intensity": self.emotional_state.I
            }

            memory.add(messages, user_id=self.user_id, metadata=metadata)
            logger.info(f"Logged interpersonal episode: {episode_id}")
            return episode_id

        except Exception as e:
            logger.exception("Failed to log episode")
            return ""

    def enable_strict_mode(self, duration_minutes: int = 25) -> Dict[str, any]:
        """Enable strict mode if within limits"""

        self._strict_sessions_today += 1
        self._last_session_time = datetime.now()

        return {
            "enabled": True,
            "duration_minutes": duration_minutes,
            "session_count": self._strict_sessions_today
        }


    def get_system_behavioral_changes(self) -> Dict[str, any]:
        """Get system-level behavioral changes based on emotional state"""
        changes = {
            "search_horizon_multiplier": 1.0,
            "exploration_budget_multiplier": 1.0,
            "quick_wins_priority": False,
            "leverage_actions_suggested": False
        }

        # High Arousal + User attribution + repeated breach → shorten search horizon
        if (self.emotional_state.A > 0.7 and
            self.emotional_state.T == Target.USER and
            self.should_escalate()):
            changes["search_horizon_multiplier"] = 0.6
            changes["quick_wins_priority"] = True

        # Low Control → suggest leverage-increasing actions
        if self.emotional_state.C < 0.4:
            changes["leverage_actions_suggested"] = True

        # Positive Valence streaks → widen exploration budget
        if self.emotional_state.V > 0.5:
            changes["exploration_budget_multiplier"] = 1.3

        return changes

def create_example_commitment(user_id: str = "1") -> str:
    """Create an example commitment for demonstration"""
    commitment_data = {
        "id": "practice_polish_daily",
        "party": "user",
        "goal_id": "learn_pl",
        "promise": "15m Polish drills on weekdays at 20:00",
        "kpi": {"sessions_per_week": 5},
        "due": "rolling",
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "grace": {"misses_before_nudge": 1, "misses_before_pushback": 3}
    }

    messages = [
        {"role": "system", "content": f"COMMITMENT: {json.dumps(commitment_data)}"}
    ]

    metadata = {
        "category": "contracts.commitments",
        "commitment_id": commitment_data["id"],
        "party": "user",
        "status": "active"
    }

    memory.add(messages, user_id=user_id, metadata=metadata)
    return commitment_data["id"]

# Usage example
def demo_affect_loop():
    """Demonstrate the enhanced affect loop"""

    # Initialize affect loop
    loop = AffectLoop(user_id="demo_user")

    # Create example commitment
    commitment_id = create_example_commitment("demo_user")

    # Create example goals
    goals = [
        Goal(
            id="learn_pl",
            utility=0.8,
            progress=0.3,
            progress_velocity=0.02,
            expected_progress=0.6,
            deadline_seconds=30*24*3600,  # 30 days
            horizon_seconds=90*24*3600,   # 90 days
            risk=0.4,
            blockers=1,
            ownership=0.9,
            evidence=0.7,
            predicted_delta=0.05,
            observed_delta=0.01  # Lower than expected
        )
    ]

    # Update emotional state
    emotional_state = loop.update_emotional_state(goals)

    # Get response style
    style = loop.get_response_style()

    # Generate response
    context = {
        "missed_task": "Polish drill at 20:00",
        "miss_count": "twice this week",
        "goal_name": "B2 by March"
    }
    template = loop.generate_response_template(context)

    # Log an episode
    episode_id = loop.log_interaction_episode(
        narrative="User missed scheduled Polish practice session",
        commitment_ids=[commitment_id]
    )

    # Check behavioral changes
    changes = loop.get_system_behavioral_changes()

    print(f"Emotional State: {emotional_state}")
    print(f"Response Style: {style}")
    print(f"Template: {template}")
    print(f"Episode ID: {episode_id}")
    print(f"System Changes: {changes}")

if __name__ == "__main__":
    demo_affect_loop()
