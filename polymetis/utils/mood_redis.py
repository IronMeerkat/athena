"""
Redis-based mood tracking for fast current mood access.
Uses DB 1 to separate from LangGraph checkpointer (DB 0).
"""

import json
import colorsys
from datetime import datetime
from typing import Optional, Dict, Literal
from enum import Enum

import redis
from athena_logging import get_logger
from athena_settings import settings
from polymetis.utils.emotional_engine import EmotionalState, Target

logger = get_logger(__name__)

_client = redis.Redis.from_url(f"redis://{settings.REDIS_URL}/1", decode_responses=True)


MoodLabel = Literal[
    "focused", "calm", "curious", "confident", "uncertain",
    "cautious", "overloaded", "frustrated", "self_critical",
    "tired", "neutral", "proud", "pleased", "disappointed",
    "annoyed", "excited", "worried"
]

class MoodSnapshot:
    """Lightweight mood snapshot for Redis storage"""
    def __init__(self, V: float, A: float, C: float, U: float, T: Target, I: float, ts: str = None):
        self.V = V
        self.A = A
        self.C = C
        self.U = U
        self.T = T
        self.I = I
        self.ts = ts or datetime.now().isoformat()
        self.label = self._compute_label()
        self.emoji = self._get_emoji()
        self.color_hex = self._compute_color()

    def _clamp(self, x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, x))

    def _compute_label(self) -> MoodLabel:
        """Compute mood label from V/A/C/U state"""
        # High positive valence states
        if self.V > 0.6 and self.A > 0.5 and self.C > 0.6:
            return "proud"
        if self.V > 0.5 and self.A > 0.6:
            return "excited"
        if self.V > 0.4 and self.A < 0.4:
            return "pleased"

        # High negative valence states with attribution
        if self.V < -0.4 and self.A > 0.6 and self.T == Target.USER:
            return "frustrated"
        if self.V < -0.3 and self.A < 0.5 and self.T == Target.USER:
            return "disappointed"
        if self.V < -0.2 and self.A > 0.4 and self.T == Target.USER:
            return "annoyed"
        if self.V < -0.2 and self.T == Target.SELF:
            return "self_critical"

        # Anxiety/uncertainty states
        if self.U > 0.7 and self.A > 0.5:
            return "worried"
        if self.U > 0.7 and self.V >= -0.2:
            return "uncertain"

        # Stress/overload
        if self.C < 0.3 and self.A > 0.6:
            return "overloaded"
        if self.A < 0.25 and self.V < 0.0:
            return "tired"

        # Positive focused states
        if self.C > 0.7 and self.V > 0.3:
            return "confident"
        if 0.35 <= self.A <= 0.65 and self.V >= 0.1 and self.C >= 0.5:
            return "focused"
        if self.A > 0.5 and self.U > 0.5 and self.V >= 0.0:
            return "curious"
        if self.A < 0.35 and self.V > 0.2:
            return "calm"
        if self.C <= 0.5 and self.U >= 0.4:
            return "cautious"

        return "neutral"

    def _get_emoji(self) -> str:
        """Get emoji for mood label"""
        emoji_map = {
            "focused": "🧭",
            "calm": "🫧",
            "curious": "🔎",
            "confident": "🛡️",
            "uncertain": "🌀",
            "cautious": "⚖️",
            "overloaded": "🔥",
            "frustrated": "💢",
            "self_critical": "🛠️",
            "tired": "🌙",
            "neutral": "🔘",
            "proud": "👑",
            "pleased": "😊",
            "disappointed": "😞",
            "annoyed": "😤",
            "excited": "⚡",
            "worried": "😰",
        }
        return emoji_map.get(self.label, "🔘")

    def _compute_color(self) -> str:
        """Compute hex color from emotional state"""
        # Hue from valence (-1..1 -> 0°(red) .. 120°(green))
        hue = self._clamp((self.V + 1.0) / 2.0, 0.0, 1.0) * (120.0 / 360.0)
        sat = self._clamp(0.2 + 0.8 * self.A, 0.0, 1.0)
        lig = self._clamp(0.5 + 0.2 * (self.C - 0.5) - 0.2 * (self.U - 0.5), 0.3, 0.8)
        r, g, b = colorsys.hls_to_rgb(hue, lig, sat)
        return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "V": self.V, "A": self.A, "C": self.C, "U": self.U,
            "T": str(self.T), "I": self.I, "ts": self.ts,
            "label": self.label, "emoji": self.emoji, "color_hex": self.color_hex
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'MoodSnapshot':
        """Create from dictionary"""
        return cls(
            V=data["V"], A=data["A"], C=data["C"], U=data["U"],
            T=Target(data["T"]), I=data["I"], ts=data["ts"]
        )

    def format_status(self) -> str:
        """Format as compact status string"""
        return f"{self.emoji} {self.label.capitalize()} (V:{self.V:.2f} A:{self.A:.2f} C:{self.C:.2f} U:{self.U:.2f})"

def _key_current(user_id: str) -> str:
    return f"athena:mood:current:{user_id}"

def _key_history(user_id: str) -> str:
    return f"athena:mood:history:{user_id}"

def set_current_mood(state: EmotionalState, user_id: str = "1",
                     ttl_seconds: int = 1800, history_max: int = 60) -> bool:
    """
    Set current mood in Redis with TTL and add to history.
    Returns True if successful, False otherwise.
    """
    if not _client:
        logger.warning("Redis client not available, skipping mood update")
        return False

    try:
        snapshot = MoodSnapshot(state.V, state.A, state.C, state.U, state.T, state.I)
        payload = json.dumps(snapshot.to_dict())

        p = _client.pipeline(transaction=True)
        p.set(_key_current(user_id), payload, ex=ttl_seconds)
        p.lpush(_key_history(user_id), payload)
        p.ltrim(_key_history(user_id), 0, history_max - 1)
        p.execute()

        logger.debug(f"Updated mood: {snapshot.format_status()}")
        return True
    except Exception as e:
        logger.exception("Failed to set current mood in Redis")
        return False

def get_current_mood(user_id: str = "1") -> Optional[MoodSnapshot]:
    """
    Get current mood from Redis. Returns None if no mood or expired.
    """

    try:
        raw = _client.get(_key_current(user_id))
        if not raw:
            return None
        data = json.loads(raw)
        return MoodSnapshot.from_dict(data)
    except Exception as e:
        logger.exception("Failed to get current mood from Redis")
        return None

def get_mood_history(user_id: str = "1", limit: int = 10) -> list[MoodSnapshot]:
    """
    Get recent mood history from Redis.
    """
    if not _client:
        return []

    try:
        raw_list = _client.lrange(_key_history(user_id), 0, limit - 1)
        snapshots = []
        for raw in raw_list:
            try:
                data = json.loads(raw)
                snapshots.append(MoodSnapshot.from_dict(data))
            except Exception:
                continue
        return snapshots
    except Exception as e:
        logger.exception("Failed to get mood history from Redis")
        return []

def is_mood_stale(user_id: str = "1") -> bool:
    """
    Check if current mood is stale (expired TTL).
    """
    return get_current_mood(user_id) is None
