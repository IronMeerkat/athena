# Future Features

Planned and proposed features, consolidated from planning docs.

## Near‑term (Phases 1–3)

- Agentic core: Sense, Classify (LLM optional), Policy, Appeal, Enforcement
- Caching & cooldowns, token/QPS budgets, strict validation of LLM outputs
- Streaming appeal UI and richer policy explanations
- Remote agents behind flags (`USE_REMOTE_AGENT`)

## Feature ideas (Backlog)

- Search‑only mode (DOM rules + DNR)
- Intent gate (typed intent + TTL)
- Adaptive strictness (per‑host profile, friction levels)
- Appeal memory (better rationale, not auto‑whitelist)
- Proactive alerts, task redirector, minimal mode, granular profiles
- Team mode (opt‑in), personalized insights, micro‑cooldowns, revisit guard
- Network‑level assists via MV3 DNR, granular allowlists

## Non‑LLM ML roadmap

- URL/Title shallow classifier (first‑pass gate)
- Rhythm/risk model for time‑based strictness
- Session intent predictor (doom‑loop detection)
- kNN personalization with local embeddings
- Feed/clickbait detector to power Minimal/Search‑only rules

Sources: `agentic-anti-distraction-plan.md`, `anti-distraction-functional-backlog.md`, `non-llm-ml-enhancements.md`.
