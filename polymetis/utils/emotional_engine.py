from pydantic import BaseModel
import numpy as np
from typing import List, Dict, Literal, Optional
from datetime import datetime, timedelta
from enum import Enum

def clamp(x, lo, hi):
    """Vectorized clamp function using numpy.clip"""
    return np.clip(x, lo, hi)

class Target(str, Enum):
    """Attribution target for emotional responsibility"""
    SELF = "self"
    USER = "user"
    EXTERNAL = "external"

class CommitmentStatus(str, Enum):
    """Status of a commitment"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    BROKEN = "broken"

class Commitment(BaseModel):
    """Bilateral promise with due dates and acceptance criteria"""
    id: str
    party: Literal["user", "athena"]
    goal_id: str
    promise: str
    kpi: Dict[str, float]  # e.g. {"sessions_per_week": 5}
    due: str  # "rolling", date string, or cron expression
    created_at: datetime
    status: CommitmentStatus
    grace: Dict[str, int]  # e.g. {"misses_before_nudge": 1, "misses_before_pushback": 3}

class Boundary(BaseModel):
    """What Athena will/won't do"""
    id: str
    description: str
    context: str  # e.g. "strict_mode", "focus_sessions"
    active: bool
    created_at: datetime

class InterpersonalEpisode(BaseModel):
    """Logged expectation-violations with emotional context"""
    id: str
    target: Target
    intensity: float
    valence: float
    arousal: float
    control: float
    uncertainty: float
    narrative: str  # short description of what happened
    commitment_ids: List[str]  # related commitments
    timestamp: datetime
    resolved: bool

class Goal(BaseModel):
    id: str
    utility: float
    progress: float
    progress_velocity: float
    expected_progress: float
    deadline_seconds: float      # seconds from now to deadline
    horizon_seconds: float       # normalization window
    risk: float                  # 0..1
    blockers: int
    ownership: float             # 0..1
    evidence: float              # 0..1
    predicted_delta: float
    observed_delta: float

class EmotionalState(BaseModel):
    """Extended emotional state with attribution and intensity"""
    V: float = 0.0  # Valence (-1 to 1)
    A: float = 0.2  # Arousal (0 to 1)
    C: float = 0.7  # Control (0 to 1)
    U: float = 0.7  # Uncertainty (0 to 1)
    T: Target = Target.SELF  # Attribution target
    I: float = 0.0  # Intensity (0 to 1)

def softmax(xs):
    """Vectorized softmax function"""
    xs = np.array(xs)
    m = np.max(xs)
    exps = np.exp(xs - m)
    return exps / np.sum(exps)

def compute_commitment_signals(commitments: List[Commitment],
                              episodes: List[InterpersonalEpisode],
                              lookback_days: int = 7) -> Dict[str, float]:
    """Compute breach signals from commitments and episodes"""
    if not commitments:
        return {"user_breaches": 0.0, "user_leverage": 0.0, "athena_fail": 0.0,
                "athena_leverage": 0.0, "ext_shocks": 0.0, "ext_leverage": 0.0,
                "impact": 0.0, "recurrence": 0.0}

    cutoff_date = datetime.now() - timedelta(days=lookback_days)
    recent_episodes = [ep for ep in episodes if ep.timestamp >= cutoff_date]

    # Count breaches by party
    user_breaches = len([ep for ep in recent_episodes if ep.target == Target.USER])
    athena_failures = len([ep for ep in recent_episodes if ep.target == Target.SELF])
    external_shocks = len([ep for ep in recent_episodes if ep.target == Target.EXTERNAL])

    # Normalize by active commitments
    active_user_commitments = len([c for c in commitments if c.party == "user" and c.status == CommitmentStatus.ACTIVE])
    active_athena_commitments = len([c for c in commitments if c.party == "athena" and c.status == CommitmentStatus.ACTIVE])

    # Compute leverage (counterfactual impact)
    user_leverage = min(1.0, active_user_commitments / max(1, len(commitments)))
    athena_leverage = min(1.0, active_athena_commitments / max(1, len(commitments)))
    ext_leverage = 0.3  # External factors have moderate leverage

    # Compute impact (utility-weighted loss)
    impact = np.mean([ep.valence for ep in recent_episodes]) if recent_episodes else 0.0
    impact = abs(impact)  # Convert to positive impact magnitude

    # Compute recurrence (EMA of similar events)
    if len(recent_episodes) >= 2:
        intervals = []
        for i in range(1, len(recent_episodes)):
            delta = (recent_episodes[i].timestamp - recent_episodes[i-1].timestamp).total_seconds() / 3600
            intervals.append(delta)
        # Shorter intervals = higher recurrence
        avg_interval = np.mean(intervals)
        recurrence = clamp(1.0 / (avg_interval / 24.0 + 1.0), 0.0, 1.0)  # Normalize by days
    else:
        recurrence = 0.0

    return {
        "user_breaches": clamp(user_breaches / max(1, active_user_commitments), 0.0, 1.0),
        "user_leverage": user_leverage,
        "athena_fail": clamp(athena_failures / max(1, active_athena_commitments), 0.0, 1.0),
        "athena_leverage": athena_leverage,
        "ext_shocks": clamp(external_shocks / max(1, len(recent_episodes)), 0.0, 1.0),
        "ext_leverage": ext_leverage,
        "impact": impact,
        "recurrence": recurrence
    }

def attribute_responsibility(signals: Dict[str, float]) -> tuple[Target, float]:
    """Determine attribution target and intensity"""
    # Compute attribution scores
    candidates = [
        (Target.USER, signals["user_breaches"] * signals["user_leverage"]),
        (Target.SELF, signals["athena_fail"] * signals["athena_leverage"]),
        (Target.EXTERNAL, signals["ext_shocks"] * signals["ext_leverage"])
    ]

    target, score = max(candidates, key=lambda x: x[1])

    # Compute intensity
    intensity = clamp(
        0.4 * signals.get("A", 0.0) +  # Arousal component
        0.4 * signals["impact"] +       # Impact component
        0.2 * signals["recurrence"],    # Recurrence component
        0.0, 1.0
    )

    return target, intensity

def appraise(goals: List[Goal],
            state: EmotionalState,
            commitments: Optional[List[Commitment]] = None,
            episodes: Optional[List[InterpersonalEpisode]] = None) -> EmotionalState:
    """Enhanced vectorized emotional appraisal function with attribution"""
    if not goals:
        return state

    # weights
    alpha1, alpha2 = 0.7, 0.3
    beta1, beta2, beta3 = 0.6, 0.3, 0.1

    # Extract goal properties into numpy arrays for vectorized operations
    utilities = np.array([g.utility for g in goals])
    deadline_seconds = np.array([g.deadline_seconds for g in goals])
    horizon_seconds = np.array([g.horizon_seconds for g in goals])
    progress = np.array([g.progress for g in goals])
    expected_progress = np.array([g.expected_progress for g in goals])
    progress_velocity = np.array([g.progress_velocity for g in goals])
    observed_delta = np.array([g.observed_delta for g in goals])
    predicted_delta = np.array([g.predicted_delta for g in goals])
    blockers = np.array([g.blockers for g in goals])
    ownership = np.array([g.ownership for g in goals])
    evidence = np.array([g.evidence for g in goals])

    # Vectorized urgencies calculation
    rem = np.maximum(0.0, deadline_seconds)
    hor = np.maximum(1.0, horizon_seconds)
    time_g = clamp(1.0 - rem/hor, 0.0, 1.0)
    urgencies = utilities * (0.5 + 0.5*time_g)
    w = softmax(urgencies)

    # Vectorized main computations
    gap_g = progress - expected_progress
    surp_g = np.abs(observed_delta - predicted_delta)
    blockers_factor = clamp(blockers/5.0, 0.0, 1.0)
    C_g = clamp(ownership * (1.0 - blockers_factor), 0.0, 1.0)
    U_g = clamp(evidence, 0.0, 1.0)

    # Weighted sums using vectorized operations
    V_star = np.sum(w * (alpha1*gap_g + alpha2*progress_velocity))
    A_star = np.sum(w * (beta1*time_g + beta2*surp_g + beta3*np.abs(progress_velocity)))
    C_star = np.sum(w * C_g)
    U_star = np.sum(w * U_g)

    # normalize
    V_star = clamp(V_star, -1.0, 1.0)
    A_star = clamp(A_star,  0.0, 1.0)   # arousal is 0..1
    C_star = clamp(C_star,  0.0, 1.0)
    U_star = clamp(U_star,  0.0, 1.0)

    # leaky integration
    decay = {"V":0.85, "A":0.60, "C":0.90, "U":0.95}
    new_V = decay["V"]*state.V + (1-decay["V"])*V_star
    new_A = decay["A"]*state.A + (1-decay["A"])*A_star
    new_C = decay["C"]*state.C + (1-decay["C"])*C_star
    new_U = decay["U"]*state.U + (1-decay["U"])*U_star

    # Compute attribution and intensity if commitments/episodes provided
    if commitments and episodes:
        signals = compute_commitment_signals(commitments, episodes)
        signals["A"] = new_A  # Add current arousal to signals
        target, intensity = attribute_responsibility(signals)
    else:
        target = state.T
        intensity = state.I

    return EmotionalState(
        V=new_V, A=new_A, C=new_C, U=new_U, T=target, I=intensity
    )

class ResponseStyle(BaseModel):
    """Response style configuration based on emotional state"""
    tone: str  # "nudge", "pushback", "accountability", "apologetic", "supportive"
    formality: float  # 0.0 (casual) to 1.0 (formal)
    directness: float  # 0.0 (indirect) to 1.0 (blunt)
    urgency: float  # 0.0 (relaxed) to 1.0 (urgent)
    actions: List[str]  # Behavioral actions to take

def map_emotional_state_to_style(state: EmotionalState) -> ResponseStyle:
    """Map emotional state (T, I, V/A/C/U) to response style and actions"""

    if state.T == Target.USER:
        if state.I <= 0.33:  # Firm nudge
            return ResponseStyle(
                tone="nudge",
                formality=0.3,
                directness=0.6,
                urgency=0.4,
                actions=[
                    "propose_smallest_viable_step",
                    "reschedule_missed_task",
                    "reduce_scope_if_needed"
                ]
            )
        elif state.I <= 0.66:  # Pushback
            return ResponseStyle(
                tone="pushback",
                formality=0.5,
                directness=0.8,
                urgency=0.7,
                actions=[
                    "enable_strict_mode",
                    "require_commitment_reply",
                    "surface_consequences"
                ]
            )
        else:  # Accountability mode
            return ResponseStyle(
                tone="accountability",
                formality=0.6,
                directness=1.0,
                urgency=0.9,
                actions=[
                    "pause_low_utility_requests",
                    "surface_stated_priorities",
                    "block_distractions",
                    "provide_override_word"
                ]
            )

    elif state.T == Target.SELF:
        return ResponseStyle(
            tone="apologetic",
            formality=0.4,
            directness=0.7,
            urgency=0.6,
            actions=[
                "apologize_once",
                "list_corrective_action",
                "gather_data_raise_certainty",
                "add_tests_telemetry"
            ]
        )

    else:  # Target.EXTERNAL
        return ResponseStyle(
            tone="adaptive",
            formality=0.3,
            directness=0.5,
            urgency=0.5,
            actions=[
                "pivot_plans",
                "reduce_scope",
                "add_buffer_time",
                "no_tone_change"
            ]
        )

def generate_tone_templates(style: ResponseStyle, context: Dict[str, str] = None) -> Dict[str, str]:
    """Generate tone templates based on style"""
    context = context or {}

    templates = {
        "nudge": f"You skipped the {context.get('missed_task', 'scheduled task')} {context.get('miss_count', 'twice')}. That conflicts with your '{context.get('goal_name', 'stated goal')}'. Let's do {context.get('reduced_scope', '15 minutes')} now; I'll set the timer.",

        "pushback": f"{context.get('miss_count', 'Three')} misses this week. {context.get('consequence', 'Progress slips')}. I'm starting strict mode for {context.get('duration', '25 minutes')}; reply STOP to override.",

        "accountability": f"You're asking me to {context.get('new_request', 'plan new features')} while you're not honoring the {context.get('blocking_commitment', 'training blocks')} that unblock it. We fix that first. Timer's armed.",

        "apologetic": f"I made an error with {context.get('error_context', 'the previous task')}. Here's what I'm doing to fix it: {context.get('corrective_action', 'gathering more data and adding safeguards')}.",

        "adaptive": f"External factors are affecting {context.get('affected_goal', 'your progress')}. Let's {context.get('pivot_action', 'adjust the plan')} to account for this."
    }

    return templates.get(style.tone, templates["nudge"])

def should_escalate_intensity(state: EmotionalState,
                            previous_episodes: List[InterpersonalEpisode],
                            escalation_threshold: int = 3) -> bool:
    """Check if intensity should escalate based on consecutive breaches"""
    if not previous_episodes:
        return False

    # Check for consecutive episodes with same target
    recent_same_target = []
    for ep in sorted(previous_episodes, key=lambda x: x.timestamp, reverse=True):
        if ep.target == state.T and not ep.resolved:
            recent_same_target.append(ep)
        else:
            break

    return len(recent_same_target) >= escalation_threshold
