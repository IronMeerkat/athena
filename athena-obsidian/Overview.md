# Overview

Athena Browser Extension is an agentic, privacy‑first anti‑distraction extension. It blocks or reduces distracting content using a background orchestrator and small cooperating agents. UI surfaces (popup, options, new‑tab, side‑panel, devtools) are independent React apps. Shared packages provide contracts, LLM provider abstraction, UI components, storage, i18n, and build tooling.

## Goals

- Reduce distraction with deterministic policy first, LLM assistance second
- Keep data local and minimize permissions
- Be fast to develop: shared configs, typed contracts, consistent page structure

## Repo layout

- `chrome-extension/`: core (manifest, background, build glue)
- `pages/`: multiple React apps (popup, options, new-tab, side-panel, devtools, content, content-ui, content-runtime)
- `packages/`: shared libraries (`contracts`, `agent-kit`, `llm`, `api-client`, `shared`, `ui`, `i18n`, `storage`, `hmr`, `vite-config`, etc.)
- `tests/`: E2E and future unit tests

See also: [[How It Works]].
