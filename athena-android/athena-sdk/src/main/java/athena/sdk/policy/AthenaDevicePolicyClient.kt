package athena.sdk.policy

import athena.sdk.api.AthenaApi

class AthenaDevicePolicyClient : DevicePolicyClient {
  override suspend fun reportAttempt(event: Attempt): Decision {
    return AthenaApi.reportAttempt(event)
  }

  override suspend fun acceptNudge(eventId: String, ttlMinutes: Int): Permit {
    return AthenaApi.acceptPermit(eventId, ttlMinutes)
  }
}


