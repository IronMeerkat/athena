# How It Works

High‑level architecture and flow.

## Architecture

- Background (service worker) orchestrator
  - Receives runtime messages, routes to agents, enforces policy, persists temp state
- Agents (see `@extension/agent-kit`)
  - Sense → Classify (optional LLM) → Policy → Appeal (LLM) → Enforcement
- Pages (popup/options/new-tab/side-panel/devtools)
  - Small React apps with consistent structure, Zustand stores
- Content surfaces
  - `content`: sensing scripts
  - `content-ui`: overlay UI
  - `content-runtime`: runtime-injected bundles
- Shared packages
  - Contracts, LLM provider, storage, UI, i18n, vite/tailwind configs

## Message flow (typical)

1. Content captures page context → sends `DOM_CAPTURED`
2. Background runs Sense → Policy
3. If block/prompt required → show modal via content‑ui
4. User appeals → Appeal agent (LLM) returns decision
5. Enforcement sets temp allow TTL, schedules alarms, requests re‑capture

## Principles

- Deterministic first, LLM second
- Typed contracts and strict validation
- Local‑first privacy, minimal permissions
- Performance: debounce, cache, budgets, MV3 lifecycle aware

More details in: `proposal-for-refactor.md` and `agentic-anti-distraction-plan.md`.
