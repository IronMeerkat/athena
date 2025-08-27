package athena.sdk.policy

import java.time.Instant

interface DevicePolicyClient {
  suspend fun reportAttempt(event: Attempt): Decision
  suspend fun acceptNudge(eventId: String, ttlMinutes: Int): Permit
}

data class Attempt(
  val deviceId: String,
  val app: String?,
  val url: String?,
  val ts: Instant
)

data class Decision(
  val decision: String,
  val ttlMinutes: Int? = null,
  val appealWs: String? = null
)

data class Permit(
  val token: String,
  val expiresAt: Instant
)


