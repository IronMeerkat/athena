
## Athena MCP Integration and New Agents Proposal

### Overview

This proposal describes how Polymetis exposes its capabilities via the Model Context Protocol (MCP), and outlines a set of new, composable agents aligned with Athena's role as secretary, pensieve/journal, fitness trainer, productivity coach, and digital wellbeing guardian.

All traffic continues to be mediated by `aegis`. The MCP server lives inside `polymetis` and provides a standard toolbox that DRF can call to orchestrate agents and policies. Direct access to agents is never granted to end clients; DRF is the traffic cop.

### MCP Server Surface (current)

- agents.list_public, agents.list_sensitive: Enumerate registered agents
- runs.execute, runs.execute_async, runs.status: Execute and monitor agent runs
- policy.schedule_get, policy.schedule_set: Read/write timeblock schedules
- policy.strictness_get, policy.goal_get: Query derived policy at “now”
- tools.list, tools.call: Inspect and invoke registered tools (scoped)

These map to existing registries and Celery tasks. The DRF gateway can call these MCP tools to coordinate multi-agent workflows.

Note on policies: schedule/strictness/goal logic has been moved under `polymetis.tools.policies` and is exposed as MCP tools (`policy.schedule_get`, `policy.schedule_set`, `policy.strictness_get`, `policy.goal_get`). The legacy `tasks/policy.py` is deprecated in favor of tool calls.

### Proposed Agents and Tools

1) Journaling Agent (Pensieve)
- Purpose: Reflect on recent behavior, synthesize insights, capture intents.
- Inputs: Conversation threads, daily highlights, mood, blockers.
- Outputs: Summaries, distilled goals, follow-ups.
- Tools:
  - memory.search_notes: semantic search over user notes/journals
  - memory.append_note: append structured entries to a journal namespace
  - events.fetch_timeline: pull recent app/site usage (sanitized)
  - tasks.create_todo: create actionable follow-ups in the user’s task system

2) Distraction Analysis Agent
- Purpose: Identify most frequent/contextual distractions to inform schedules.
- Inputs: Browser/activity logs, prior schedules.
- Outputs: Top distractors, temporal patterns, suggestions.
- Tools:
  - logs.query_usage({range, filters}): aggregate app/site usage
  - vector.explain_pattern: retrieve similar prior episodes and outcomes
  - policy.suggest_strictness_windows: propose stricter blocks for hotspots

3) Strictness Deliberator Agent
- Purpose: Negotiate strictness with the user and other agents for upcoming blocks.
- Inputs: Goals, distraction analysis, calendar constraints.
- Outputs: Per-block strictness proposals and rationale.
- Tools:
  - policy.simulate_block({start,end,days,strictness}): predict outcomes/costs
  - push.send_nudge: poll user preferences asynchronously

4) Goals & Scheduler Agent (existing, expanded)
- Purpose: Turn goals into a weekly schedule with per-block strictness.
- Inputs: Journaling summaries, strictness proposals, distractions.
- Outputs: Updated schedule (Redis), assistant response.
- Tools:
  - memory.get_recent_intents
  - policy.schedule_set / schedule_get (now exposed as tools under `tools.policies`)
  - calendar.read_busy_times (future: source from device/Google/Apple)

5) Workout Planner Agent
- Purpose: Program progressive overload, adapt from last week’s performance.
- Inputs: Prior workouts, recovery, HRV, sleep.
- Outputs: Weekly plan, daily prescriptions, progression targets.
- Tools:
  - wearable.galaxy_watch.fetch({metrics, range})
  - fitness.estimate_1rm({lift, reps, rpe})
  - fitness.progression_suggest({history, constraints})
  - policy.schedule_set (to place workouts in calendar blocks)

6) Appeals Agent (existing, expanded)
- Purpose: Evaluate unblock requests with context from journal and goals.
- Inputs: Current goal/strictness, page/app context, user justification.
- Outputs: allow|deny + minutes + message.
- Tools:
  - memory.search_notes (find commitments and recent reflections)
  - policy.strictness_get / goal_get (now exposed as tools under `tools.policies`)
  - push.send_block_signal / push.send_unblock_signal

7) Digital Wellbeing Coach
- Purpose: Ongoing guidance on dopamine hygiene and sleep-friendly usage.
- Inputs: Nightly usage, late-night app patterns, blue-light exposure proxies.
- Outputs: Interventions, bedtime wind-down suggestions, app substitution ideas.
- Tools:
  - logs.query_usage({after: 21:00})
  - push.send_nudge({message, context})
  - policy.schedule_set (create quiet hours)

8) Secretary/Task Router Agent
- Purpose: Intake requests across domains and route to the right specialist.
- Inputs: Free-form user directives.
- Outputs: Routed tool/agent invocations, confirmations.
- Tools:
  - tools.list + tools.call (broker calls via DRF)
  - agents.list_* + runs.execute_async (fan-out orchestration)

### Data and Safety Principles

- DRF mediates credentials and manifests. MCP calls use capability manifests to scope allowed agent IDs, tools, and memory namespaces.
- Sensitive tools (push, wearable, logs) sit behind the sensitive queue; public agents run with minimal capabilities.
- Audit fields are added to manifests and persisted with runs for traceability.

### Phased Implementation

Phase 1 (done here):
- MCP server exposing agents, runs, policy (as tools), tool registry.
- Moved schedule/strictness/goal under `tools.policies`; deprecated `tasks/policy.py`.

Phase 2:
- Add memory tools: notes search/append; activity logs query.
- Add wearable bridge: Galaxy Watch ingestion task + tool surface.
- Implement Strictness Deliberator and Distraction Analysis agents.

Phase 3:
- Implement Secretary Router and Digital Wellbeing Coach.
- Calendar integration for scheduling (readonly → read/write).

### Example Workflow (end-to-end)

1) User journals → Journaling Agent summarizes intents and creates follow-ups.
2) Distraction Analysis Agent ranks hotspots; Strictness Deliberator proposes levels.
3) Scheduler consolidates into weekly blocks and persists via policy.schedule_set.
4) Workout Planner pulls Galaxy Watch data, plans weekly progression, writes blocks.
5) Guardian enforces; Appeals Agent consults notes and current goal to adjudicate.

This keeps DRF in control: DRF constructs capability manifests per step and uses MCP tools to coordinate background runs and stream results.


