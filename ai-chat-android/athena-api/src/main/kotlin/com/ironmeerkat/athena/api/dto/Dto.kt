package com.ironmeerkat.athena.api.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

/**
 * Request body for POST /api/runs
 * - agent_id: which agent to run on the Athena side (e.g., "guardian").
 * - input: arbitrary JSON the agent understands (we keep it flexible using JsonElement).
 * - options: flags for routing/behavior (e.g., { "sensitive": true }).
 */
@Serializable
data class CreateRunRequest(
  @SerialName("agent_id") val agentId: String,
  val input: JsonElement? = null,
  val options: Map<String, JsonElement> = emptyMap(),
)

/** Response for POST /api/runs */
@Serializable
data class CreateRunResponse(
  @SerialName("run_id") val runId: String,
  val queued: Boolean,
)

/** Request for POST /api/device/attempt */
@Serializable
data class DeviceAttemptRequest(
  @SerialName("device_id") val deviceId: String,
  @SerialName("event_id") val eventId: String? = null,
  val app: String? = null,
  val url: String? = null,
  val ts: String? = null,
)

/** Response for POST /api/device/attempt */
@Serializable
data class DeviceAttemptResponse(
  @SerialName("run_id") val runId: String,
  val decision: String,
  val sse: String,
)

/** Request for POST /api/device/permit */
@Serializable
data class DevicePermitRequest(
  @SerialName("event_id") val eventId: String,
  @SerialName("ttl_minutes") val ttlMinutes: Int,
)

/** Response for POST /api/device/permit */
@Serializable
data class DevicePermitResponse(
  val granted: Boolean,
  val until: String,
)


