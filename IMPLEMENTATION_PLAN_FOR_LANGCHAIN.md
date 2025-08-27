Alright, here’s the “how Athena thinks” tour—agents, tools, messages, and that moment when you try to open TikTok at 2am and Athena gives you The Look.

## Big picture

* **DRF** is the traffic cop. It authenticates, builds a **capability manifest**, and routes a job to the right **LangChain worker** (public or sensitive) through RabbitMQ. Short-term state lives in Redis (run status, websockets sessions, “strictness” scores).
* **Athena-LangChain** is a *graph of agents* (specialized planners/executors) wired together with *tools* (side-effecty abilities like reading memories, checking schedules, toggling device policies, sending a nudge, etc.).

Think of it as a flow network, not a single mega-prompt.

---

## Core agents (the brain)

* **Context Assembler**: pulls only the allowed memory namespaces (e.g., `pensive:goals:private` for owner, `goals:policy_view` for partner), recent schedule blocks, device state, and last few interactions.
* **Schedule Planner**: turns goals into time blocks with policy IDs (focus, social, sleep). Writes to `schedule:blocks`.
* **Distraction Guardian**: the gatekeeper for app/website attempts. Decides **allow / soft-nudge / hard-block / appeal**.
* **Nudge Heuristics**: computes when to send gentle pokes (frequency, tone, channel).
* **Appeals Mediator**: runs a short, time-boxed dialogue over WebSocket when you contest a block; can grant a **temporary permit token** or uphold the block.
* **Audit & Policy Writer**: records outcomes, cooldowns, and any adjusted strictness.

These run inside **two workers**:

* **Public worker** → no sensitive memories or tools.
* **Sensitive worker** → has the private memories and stronger tools. DRF routes here only for you (owner) or pre-granted cases.

---

## Core tools (the hands)

* **PolicyStore**: read/write `schedule:blocks`, per-app rules, cooldowns, grace counters.
* **Memory API**: namespaced vector/kv access (read within manifest; writes tagged by role).
* **DeviceController**: sends signed commands to the phone (activate policy X for Y minutes, show toasts, display block screen).
* **AppClassifier**: maps package/URL → category (short-form video, messaging, work).
* **RateLimiter**: tracks per-app/session limits, doses “just one more” allowances.
* **Notifier**: FCM/Web Push.
* **Cost/Time Guards**: ceilings for tokens/time (safety rails).

---

## The app/website attempt flow (phone → DRF → LangChain → decision)

**Scenario**: you tap an app or open a site.

1. **Phone → DRF**
   The device sends an intent like:

   * `POST /api/device/attempt`
     Body: `{ "device_id": "X", "event_id": "uuid", "app": "com.foo", "url": null, "ts": "..." }`
     The device also has the *current policy ID* and a cached allowlist/denylist for instant blocks (for obvious cases).

2. **DRF resolves role & manifest**

   * Looks up the actor (you), current block, role, and builds a **Capability Manifest**.
   * Decides the lane: owner requests → **sensitive** worker; guest/partner nudges → **public** worker.

3. **DRF → RabbitMQ → LangChain**

   * Enqueue `runs.execute_graph(agent="distraction_guardian", payload={attempt,...}, manifest=...)` to the proper vhost/queue.
   * Start an SSE stream for this `event_id` (the device can watch a “decision pending” spinner for a few hundred ms).

4. **Distraction Guardian (in worker)**

   * **Context Assembler** pulls: active block, policies, strictness, your goals’ abstract, recent behavior (nudges given, prior overrides), and classifier hits for the app/site.
   * **Decision**:

     * **ALLOW** if it’s within the block’s whitelist or fits a permitted “micro-break”.
     * **NUDGE** if you’re slightly off-block or late into a period where a micro-break is okay: “2 minutes, then back to deep work?”
     * **BLOCK** if it clearly violates current policy, and cooldowns say “nope”.
     * **APPEAL** if ambiguous or your recent compliance earns a hearing.

5. **Worker → DRF → Device**

   * DRF relays the decision via SSE to the device.
   * **ALLOW** → Device opens app/site.
   * **NUDGE** → Device shows nudge UI (with a one-tap “OK 2 min” that creates a *temporary permit token*).
   * **BLOCK** → Device shows a block screen with a “Appeal” button.
   * **APPEAL** → DRF opens a **WebSocket** room `/ws/appeals/{event_id}` and the **Appeals Mediator** spins up.

6. **Appeals chat (WebSocket)**

   * Short, rules-based dialogue (“what’s the goal here?”, “can it wait?”, “2-minute window acceptable?”).
   * Time-boxed, e.g., ≤ 60 seconds; the mediator references your goals *at abstraction level*, not private details.
   * Outcomes:

     * **Grant temporary permit** (e.g., 2–5 minutes; logged).
     * **Uphold block** (with rationale).
   * Device enforces immediately via `DeviceController`. Results are audited and strictness adjusted slightly.

7. **Post-decision updates**

   * **Audit & Policy Writer** updates counters (nudges used, permits, overrides).
   * **Schedule Planner** may learn: “meetings days lower strictness on social after 9pm” (slow adaptation, not whiplash).

> Latency target: ALLOW/NUDGE/BLOCK in \~100–300ms (fast path). Appeals is human-paced via WebSocket.

---

## How strictness works (and evolves)

**Strictness** is a score (say 0–100) per context (global and per category/app). It’s computed from:

* Current block intent (deep work, social, rest).
* Recent compliance (obeyed nudges? blew through permits?).
* Fatigue/time of day (softening late at night can be harmful—Athena learns your patterns).
* Goal proximity (deadlines raise strictness for related categories).
* Manual overrides (owner can pin ranges).

Effects of strictness:

* Thresholds for **auto-allow** vs **nudge** vs **block**.
* Cooldown lengths and “micro-break” allowances.
* Whether appeals are offered or immediately denied.

It moves **gradually** (exponential smoothing, caps per hour) to avoid yoyo behavior.

---

## When Athena nudges vs blocks

* **Nudge** when:

  * You’re close to allowed behavior (e.g., finishing a block).
  * A micro-break won’t meaningfully harm momentum.
  * Recent compliance is good.
* **Block** when:

  * You’re early in a deep focus block.
  * Strictness is high due to repeated slips or goal urgency.
  * App/site is categorized as a strong distractor with no contextual justification.

Nudges are specific and time-boxed (“2 minutes, then we close this”). Blocks are short, firm, and offer **Appeal**.

---

## Conversational goals (owner chats)

* You and Athena regularly discuss goals in a private **Goals Session** (sensitive lane). The **Schedule Planner** converts these into:

  * Objective → sub-goals → habits → **time blocks** tagged with **policies**.
  * A **policy\_view** summary that’s safe for other roles (no sensitive details).
* The **Nudge Heuristics** agent learns your tolerance and preferred tone (gentle vs blunt; phone vs desktop).

---

## Suggested extra endpoints for the device flow

* `POST /api/device/attempt` → returns `{decision: "allow|nudge|block|appeal", permit_ttl?:int, appeal_ws?:url}`
* `POST /api/device/permit` → exchange a nudge offer for a signed **temporary permit token**
* `GET /api/runs/{event_id}/events` (SSE) → decision streaming
* `WS /ws/appeals/{event_id}` → mediator chat
* `POST /api/device/decision_ack` → device confirms it applied the command (for audit)

(Existing `/api/policies/activate`, `/api/devices/{id}/state`, etc., still apply.)

---

## Control: partner & guests

* Partner can trigger **policy switches** (pre-granted, bounded) like `social_mode` for a limited TTL—but the **Appeals Mediator** and block decisions for your private focus remain strictly in the sensitive lane with private memories inaccessible to partner requests.

---

## Putting it together—mental flowchart (textual)

1. **Attempt** → DRF builds manifest → queue.
2. **Assemble context** (schedule, strictness, category, recent actions).
3. **Guardian decides**: allow / nudge / block / appeal.
4. **If nudge** → device shows “2 minutes?” → if yes, **permit**; if no, block or appeal.
5. **If appeal** → WS chat → grant permit or uphold block.
6. **Device enforces** → audit → adjust strictness slightly → maybe notify (subtle toast).

That’s the choreography: one Athena, one traffic cop, two worker lanes, and a tidy dance between fast decisions and humane appeals. If you want, I can turn this into a small UML-ish sequence diagram and drop it into your repo so Cursor has something visual to follow.
