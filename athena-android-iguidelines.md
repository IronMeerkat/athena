Awesome plan. You’re basically fusing **DigiPaws** (app/site blocking engine) with **skydoves/chatgpt-android** (a Compose chat shell wired for AI messaging). Below is a **Cursor-ready migration recipe**: what to copy, what to keep, how to wire DRF/FCM/SSE/WS, and a clean UI plan.

I checked both repos so the guidance matches their intent/features. DigiPaws is an open-source blocker with usage stats, widgets, accessibility/Shizuku utilities; skydoves/chatgpt-android is a Compose chat app scaffolded with Stream Chat patterns for a GPT-like UI. ([GitHub][1])

---

# 0) Strategy—keep the chassis, drop in the engine

* **Use `chatgpt-android` as the host app** (package name, app module, Compose navigation, theming).
* **Import DigiPaws as a new Gradle module** (`:digipaws-core`) and expose a small blocking API to the host.
* Add an **Athena SDK layer** for DRF calls (SSE/WS, FCM registration, device attempt/permit).

This keeps chat UX/dev-ex from skydoves and leverages DigiPaws’ enforcement.

---

# 1) Project structure (Cursor: create exactly)

```
/athena-android/
  settings.gradle.kts
  build.gradle.kts
  gradle/libs.versions.toml

  app/                               # from chatgpt-android (host)
    src/main/AndroidManifest.xml
    src/main/kotlin/com/ironmeerkat/athena/...
    src/main/res/...

  digipaws-core/                     # new module (ported from DigiPaws)
    src/main/AndroidManifest.xml
    src/main/java/nethical/digipaws/...   # keep original packages inside module
    src/main/res/...

  athena-sdk/                        # new: DRF client & device policy client
    src/main/kotlin/athena/sdk/api/...
    src/main/kotlin/athena/sdk/policy/...
    src/main/kotlin/athena/sdk/push/...

```

**settings.gradle.kts**

```kotlin
include(":app", ":digipaws-core", ":athena-sdk")
```

**app/build.gradle.kts** — add:

```kotlin
dependencies {
  implementation(project(":digipaws-core"))
  implementation(project(":athena-sdk"))
  implementation(libs.okhttp)
  implementation(libs.okhttp.logging)
  implementation(libs.kotlinx.coroutines)
  implementation(libs.androidx.datastore)
  implementation(libs.firebase.messaging) // FCM
}
```

---

# 2) What to copy from DigiPaws (and where)

From DigiPaws, bring over the **blocking engine bits**; keep their package namespace *inside* your `:digipaws-core` module to minimize refactors:

* **Services / Permissions**

  * `AccessibilityService` (core for overlay/keyword blocking)
  * (If present) `NotificationListenerService` (for keyword blocking in notifications)
  * `UsageStats` utilities (app detection, stats)
  * `Overlay`/“block screen” activity

* **Data**

  * App/category rules, keyword filters, schedule policy model
  * Local storage (Room/Datastore) of rules & counters

* **Blocker**

  * Interceptor that detects foreground app/URL (via Usage Stats + Accessibility events)
  * Decision pipeline that currently shows DigiPaws’ block UI → **we will reroute to Fireside’s UI and DRF**

> Leave DigiPaws’ standalone UI out; you’ll use `app/` (skydoves) screens.

**digipaws-core/AndroidManifest.xml**: declare services but mark them **exported=false** and **permission-protected** where applicable.

---

# 3) Wire the host app (chat shell) to the blocker

In `athena-sdk`, add a tiny **DevicePolicyClient** that is the single portal the DigiPaws engine calls when a decision is needed.

```kotlin
// athena-sdk/policy/DevicePolicyClient.kt
interface DevicePolicyClient {
  suspend fun reportAttempt(event: Attempt): Decision   // fast path (ALLOW/NUDGE/BLOCK/APPEAL)
  suspend fun acceptNudge(eventId: String, ttlMinutes: Int): Permit
}

data class Attempt(val deviceId: String, val app: String?, val url: String?, val ts: Instant)
data class Decision(val decision: String, val ttlMinutes: Int? = null, val appealWs: String? = null)
data class Permit(val token: String, val expiresAt: Instant)
```

**DigiPaws → Athena bridge**
Where DigiPaws today decides to show its own block screen, replace with:

```kotlin
val decision = devicePolicyClient.reportAttempt(
  Attempt(deviceId, currentApp, currentUrl, Instant.now())
)
when (decision.decision) {
  "allow" -> proceed()
  "nudge" -> showNudgeUI(decision.ttlMinutes!!)
  "block" -> showBlockUI(eventId)
  "appeal"-> openAppeals(eventId = currentEventId, ws = decision.appealWs!!)
}
```

---

# 4) DRF integration (HTTP + SSE + WS)

**athena-sdk/api/AthenaApi.kt**

```kotlin
object AthenaApi {
  private val client = OkHttpClient.Builder().build()
  private val base = BuildConfig.API_BASE

  suspend fun reportAttempt(attempt: Attempt): Decision = post("/api/device/attempt", attempt)
  suspend fun acceptPermit(eventId: String, ttl: Int): Permit = post("/api/device/permit", mapOf("event_id" to eventId, "ttl_minutes" to ttl))

  fun openAppeals(eventId: String): WebSocket {
    val req = Request.Builder().url("${BuildConfig.WS_BASE}/ws/appeals/$eventId").build()
    return client.newWebSocket(req, YourWsListener())
  }
}
```

**SSE** (if you want live decision streaming):

```kotlin
fun subscribeRun(runId: String, onEvent: (String)->Unit): Call {
  val req = Request.Builder().url("${BuildConfig.API_BASE}/api/runs/$runId/events").build()
  val call = client.newCall(req)
  call.enqueue(object: Callback { /* parse event-stream lines */ })
  return call
}
```

---

# 5) Android Manifest & permissions (host app)

In `app/src/main/AndroidManifest.xml`, **request** and **explain**:

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
<uses-permission android:name="android.permission.PACKAGE_USAGE_STATS" tools:ignore="ProtectedPermissions"/>
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<!-- Optional if using NotificationListener -->
<uses-permission android:name="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE" />
```

Declare services from `:digipaws-core`:

```xml
<service
  android:name="nethical.digipaws.access.DigiPawsAccessibilityService"
  android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"
  android:exported="false">
  <intent-filter>
    <action android:name="android.accessibilityservice.AccessibilityService" />
  </intent-filter>
</service>
```

If using overlays, ensure you request `SYSTEM_ALERT_WINDOW` via Settings screen when app starts.

---

# 6) DI & module boundaries

* Keep DigiPaws logic **pure-Kotlin** where possible; side-effects (toasts, overlays) should be overridable so the host app can show **Fireside UI** instead.
* Inject `DevicePolicyClient` via a simple Service Locator or Hilt in the host `app/` and pass it into `digipaws-core` entry points.

---

# 7) Networking & push

* **FCM**: register token on boot/refresh → `POST /api/push/fcm/register { device_id, fcm_token }`

* Receive pushes: `FirebaseMessagingService.onMessageReceived()` routes:

  * “decision ready” → open correct screen
  * “nudge expiring” → show countdown UI
  * “policy switched” → banner

* **Retry**: use `WorkManager` for offline attempt/permit retries.

---

# 8) UI plan (Compose) — Cursor-ready components

### Screens

* `HomeScreen()`

  * `ActivePolicyBanner(policyName, ttl)`
  * `TodayScheduleCard(blocks)`
  * `RecentNudgesList()`
* `ChatScreen()` (reuse skydoves’ chat thread; wire to DRF `/api/runs`)
* `BlockScreen(eventId, reasonTag, onAppeal)`
* `NudgeSheet(eventId, ttl, onAccept, onDecline)`
* `AppealsScreen(eventId)` (WebSocket chat, 60s countdown)
* `GoalsScreen()` (owner only)
* `SettingsScreen()` (permissions checklist: Accessibility, Usage Access, Overlay, Notifications)

### Navigation

```
Home -> Chat
Home -> Goals
BlockScreen -> AppealsScreen
NudgeSheet (modal) -> closes to previous
```

### Components (snippets)

```kotlin
@Composable
fun ActivePolicyBanner(name: String, ttl: Duration, onDetails: ()->Unit) {
  Surface(tonalElevation = 2.dp, shape = RoundedCornerShape(16.dp)) {
    Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
      Icon(Icons.Default.Shield, contentDescription = null)
      Spacer(Modifier.width(8.dp))
      Column(Modifier.weight(1f)) {
        Text("Policy: $name", style = MaterialTheme.typography.titleMedium)
        Text("Ends in ${ttl.inWholeMinutes} min", style = MaterialTheme.typography.bodySmall)
      }
      TextButton(onClick = onDetails) { Text("Details") }
    }
  }
}
```

```kotlin
@Composable
fun BlockScreen(reason: String, onAppeal: ()->Unit, onBackToWork: ()->Unit) {
  Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center, horizontalAlignment = Alignment.CenterHorizontally) {
    Icon(Icons.Default.Block, contentDescription = null, modifier = Modifier.size(72.dp))
    Spacer(Modifier.height(16.dp))
    Text("Blocked", style = MaterialTheme.typography.headlineSmall)
    Text(reason, style = MaterialTheme.typography.bodyMedium)
    Spacer(Modifier.height(24.dp))
    Row {
      OutlinedButton(onClick = onBackToWork) { Text("Back to work") }
      Spacer(Modifier.width(12.dp))
      Button(onClick = onAppeal) { Text("Appeal") }
    }
  }
}
```

---

# 9) Event flow (device → DRF) glue

**On foreground app change / URL attempt (from DigiPaws engine):**

1. Generate `eventId = UUID`.
2. `DevicePolicyClient.reportAttempt(Attempt(...))`
3. Handle `Decision`:

   * `allow` → no UI
   * `nudge` → `NudgeSheet(eventId, ttl)`
   * `block` → `BlockScreen(eventId, reason)`
   * `appeal` → navigate `AppealsScreen(eventId)` and open WS

**On nudge accept:**

* Call `AthenaApi.acceptPermit(eventId, ttl)`, store token and allow temporarily.

**On TTL end:**

* Overlay gentle “Time’s up” and auto-exit the distractor.

---

# 10) Cursor “Project Rules” delta for the client

* **Do not** change module names: `:app`, `:digipaws-core`, `:athena-sdk`.
* **Do not** modify packages under `nethical.digipaws.*`; wrap them via interfaces.
* All device → DRF messages go through `athena-sdk`.
* WebSocket endpoints fixed: `/ws/appeals/{event_id}`; SSE not required on Android if FCM present.
* Permissions must be requested via a single **Permissions Hub** screen; don’t scatter dialogs.

---

# 11) Risks & gotchas

* **Accessibility killers** on OEMs: add a health check loop that re-prompts user to re-enable Accessibility if killed.
* **Overlay permission**: route user to `ACTION_MANAGE_OVERLAY_PERMISSION`.
* **Battery optimizations**: show a one-time prompt to whitelist the app (optional).
* **Shizuku mode** (advanced): hide behind a dev toggle; not essential for v1.

---

# 12) Minimal tasks list (handoff to Cursor)

1. Create modules `:digipaws-core` and `:athena-sdk`.
2. Copy DigiPaws’ **AccessibilityService**, usage stats utils, and block overlay to `:digipaws-core`.
3. Add `DevicePolicyClient` interface; implement `AthenaDevicePolicyClient` in `:athena-sdk`.
4. Replace DigiPaws’ internal UI calls with `DevicePolicyClient` decisions (allow/nudge/block/appeal).
5. Implement `AthenaApi.reportAttempt` & `acceptPermit`.
6. Build Compose screens: `BlockScreen`, `NudgeSheet`, `AppealsScreen`, `ActivePolicyBanner`.
7. Wire navigation from blocker callbacks to UI.
8. Register FCM token and call `/api/push/fcm/register`.
9. Add Permissions Hub screen (Accessibility, Usage Access, Overlay, Notifications).
10. E2E test: attempt → DRF decision → UI → permit or appeal.

---

If you want, I can produce a **starter branch** layout (Gradle settings, module skeletons, manifests, and the `DevicePolicyClient` + `AthenaApi` stubs) ready to paste into Cursor so it scaffolds the rest without wandering.

[1]: https://github.com/nethical6/digipaws?utm_source=chatgpt.com "nethical6/digipaws: Free App Blocker for android"
[2]: https://github.com/nethical6/digipaws/blob/kt-rewrite/app/src/main/java/nethical/digipaws/utils/ShizukuRunner.kt?utm_source=chatgpt.com "ShizukuRunner.kt - nethical6/digipaws"
