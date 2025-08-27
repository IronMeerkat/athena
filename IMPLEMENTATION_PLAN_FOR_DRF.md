In this design, the **DRF service is Athena’s “traffic cop.”** Its job isn’t to run graphs itself, but to decide who can ask for what, wrap that into a manifest, and hand it off safely to the workers.

Here’s what DRF does:

* **Authentication & roles**

  * Knows who’s talking (owner, partner, guest).
  * Maps external IDs (Discord, WhatsApp, app login) → Athena user/role.

* **Policy enforcement**

  * Builds a **capability manifest** for each request: which agents/tools/memories/policies this role is allowed to touch.
  * Rejects disallowed requests at the gate.

* **Task routing**

  * Enqueues jobs into RabbitMQ with the manifest, choosing the right vhost/queue (`public` vs `sensitive`).
  * Workers only ever see jobs they’re allowed to.

* **Streaming & push**

  * Provides **SSE/WebSocket endpoints** so clients (React, Android) can watch runs stream tokens/events.
  * Has hooks/placeholders for **Firebase (FCM)** and **Web Push (VAPID)** to notify devices when they’re in the background.

* **Control plane**

  * Exposes REST endpoints for:

    * Submitting runs (`/runs`).
    * Policy switches (`/policies/activate`).
    * Safewords/overrides.
    * Health checks (`/api/ping`).

* **Observability**

  * Logs/audits who ran what agent/tool, how much it cost, and how long it took.
  * Provides rate limits and spend caps per role.

So: **DRF is Athena’s brainstem**—auth, manifests, policy, routing, streaming. The LangChain workers are the cortex, doing the heavy thinking. Redis is the short-term RAM. RabbitMQ is the spinal cord shuttling messages.

Perfect—here’s a clean, “Cursor-friendly” summary of the DRF API surface. It’s split into what’s already stubbed in the boilerplate vs. what’s planned. Shapes are compact so Cursor won’t hallucinate fields.

# Core (implemented as stubs in the boilerplate)

**GET `/api/ping`**
Purpose: health check.
Response:

```json
{ "status": "ok" }
```

**POST `/api/runs`**
Purpose: submit a run (DRF builds a capability manifest, enqueues to RabbitMQ).
Auth: required (role resolved to owner/partner/guest).
Request:

```json
{
  "agent_id": "string",
  "input": { "text": "string", "meta": { } },     // shape is up to you
  "options": { "stream": true }                   // optional flags
}
```

Response:

```json
{ "run_id": "uuid", "queued": true }
```

**GET `/api/runs/{run_id}/events`**  (SSE)
Purpose: live stream of run events/tokens.
Headers: `Accept: text/event-stream`
Emits lines like:

```
event: token
data: {"run_id":"...","seq":12,"delta":"hello"}

event: complete
data: {"run_id":"...","status":"ok"}
```

**WebSocket `ws/echo/`**
Purpose: placeholder channel (you’ll replace with a real stream, e.g., `/ws/runs/{run_id}`).

---

# Control plane (designed; you’ll fill logic)

**POST `/api/policies/activate`**
Purpose: switch device/app policy (e.g., `social_mode`) using pre-granted capabilities.
Auth: partner/owner.
Request:

```json
{ "policy_id": "social_mode", "duration_minutes": 30, "device_id": "optional" }
```

Response:

```json
{ "accepted": true, "ttl_minutes": 30 }
```


Response:

```json
{ "unlocked": true, "until": "2025-08-27T22:10:00Z" }
```

**GET `/api/devices/{device_id}/state`**
Purpose: read current policy state (redacted; name only).
Response:

```json
{ "device_id": "abc", "policy": "social_mode", "expires_at": "..." }
```

**POST `/api/consents/pregrants`**
Purpose: owner defines partner’s allowed actions/caps.
Request:

```json
{
  "role": "partner",
  "action_id": "activate_social_mode",
  "max_minutes": 30,
  "cooldown_minutes": 720,
  "expires_at": "2025-12-31T23:59:59Z"
}
```

Response:

```json
{ "id": "pg_123", "saved": true }
```

---

# Push & subscriptions

**POST `/api/push/fcm/register`**
Purpose: register Android device token.
Request:

```json
{ "device_id": "abc", "fcm_token": "..." }
```

Response:

```json
{ "registered": true }
```

**POST `/api/push/web/subscribe`** (VAPID/Web Push)
Purpose: save browser subscription.
Request: (raw subscription from `pushManager.subscribe`)

```json
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/...",
  "keys": { "p256dh": "...", "auth": "..." },
  "ua": "optional"
}
```

Response:

```json
{ "subscribed": true }
```

---

# Platform adapters (one traffic cop)

**POST `/discord/interactions`**
Purpose: Discord slash commands → normalize → `/api/runs` or `/api/policies/activate`.
Note: verifies `X-Signature-Ed25519` / `X-Signature-Timestamp`.
Response (immediate ACK to Discord):

```json
{ "type": 5 }  // deferred response
```

**GET/POST `/whatsapp/webhook`** (Cloud API)
Purpose: WhatsApp inbound → normalize → `/api/runs` or control actions.
GET (verify):

```
?hub.mode=subscribe&hub.challenge=...&hub.verify_token=...
```

POST: verify `X-Hub-Signature-256`, parse messages, enqueue.

---

# (Optional) Admin/observability

**GET `/api/runs/{run_id}`**
Purpose: run status snapshot (in case client missed SSE).
Response:

```json
{ "run_id": "...", "status": "running|complete|error", "started_at": "...", "ended_at": null }
```

**GET `/api/audit/logs`**
Purpose: paginated audit events (owner only).
Query: `?since=...&limit=...`
Response:

```json
{ "events": [ { "ts":"...", "actor":"partner", "action":"policy.activate", "target":"device:abc" } ] }
```

---

## Notes to keep Cursor honest

* All endpoints are **under `/api/*`** except platform webhooks (`/discord/*`, `/whatsapp/*`) and websockets (`/ws/*`).
* `run_id` is a string/uuid; **don’t** assume DB schema here.
* SSE returns `text/event-stream` and **never** closes until complete/timeout.
* RabbitMQ is **internal**; no HTTP surface—routing happens via Celery inside DRF.
* Capability Manifest is **server-side** (built per request); clients don’t send it.

If you want, I can emit minimal DRF `urls.py` + view stubs for `/api/runs`, `/api/runs/{id}/events`, and `/api/policies/activate` exactly as above so Cursor can scaffold them without inventing fields.


