package athena.sdk.api

import athena.sdk.BuildConfig
import athena.sdk.policy.Attempt
import athena.sdk.policy.Decision
import athena.sdk.policy.Permit
import com.google.android.gms.tasks.Tasks
import com.google.firebase.auth.FirebaseAuth
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Interceptor
import okhttp3.Response

private class FirebaseAuthInterceptor : Interceptor {
  override fun intercept(chain: Interceptor.Chain): Response {
    val original = chain.request()
    val currentUser = FirebaseAuth.getInstance().currentUser
    val token = try {
      currentUser?.let { user ->
        Tasks.await(user.getIdToken(false))?.token
      }
    } catch (t: Throwable) {
      null
    }
    val req = original.newBuilder().apply {
      if (!token.isNullOrBlank()) header("Authorization", "Bearer $token")
    }.build()
    return chain.proceed(req)
  }
}

object AthenaApi {
  private val client = OkHttpClient.Builder()
    .addInterceptor(FirebaseAuthInterceptor())
    .build()
  private const val base = BuildConfig.ATHENA_BASE_URL

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


