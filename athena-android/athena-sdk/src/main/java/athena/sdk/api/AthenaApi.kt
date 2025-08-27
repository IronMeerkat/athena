package athena.sdk.api

import athena.sdk.policy.Attempt
import athena.sdk.policy.Decision
import athena.sdk.policy.Permit
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

object AthenaApi {
  private val client = OkHttpClient.Builder().build()
  private const val base = "https://example.invalid" // TODO: replace via BuildConfig

  suspend fun reportAttempt(attempt: Attempt): Decision {
    val body = "{}".toRequestBody("application/json".toMediaType())
    val req = Request.Builder().url("$base/api/device/attempt").post(body).build()
    client.newCall(req).execute().use {
      return Decision(decision = "allow")
    }
  }

  suspend fun acceptPermit(eventId: String, ttl: Int): Permit {
    val body = "{}".toRequestBody("application/json".toMediaType())
    val req = Request.Builder().url("$base/api/device/permit").post(body).build()
    client.newCall(req).execute().use {
      return Permit(token = "dev", expiresAt = java.time.Instant.now())
    }
  }
}


