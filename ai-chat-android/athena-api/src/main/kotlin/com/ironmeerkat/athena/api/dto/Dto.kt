package com.ironmeerkat.athena.api.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

// ---- Auth (JWT) ----

@Serializable
data class TokenObtainPairRequest(
  val username: String,
  val password: String,
)

@Serializable
data class TokenObtainPairResponse(
  val access: String,
  val refresh: String,
)

@Serializable
data class TokenRefreshRequest(
  val refresh: String,
)

@Serializable
data class TokenRefreshResponse(
  val access: String,
)

@Serializable
data class TokenVerifyRequest(
  val token: String,
)

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
  val title: String = "",
  val url: String? = null,
  val app: String? = null,
  val ts: String? = System.currentTimeMillis().toString(),
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

// ---- Chats ----

@Serializable
data class ChatsListResponse(
  val chats: List<ChatSummary>,
)

@Serializable
data class ChatSummary(
  val id: String,
  val title: String = "",
  @SerialName("updated_at") val updatedAt: String,
  @SerialName("last_message") val lastMessage: ChatMessageDto? = null,
)

@Serializable
data class ChatMessagesResponse(
  val chat: ChatDetail,
  val messages: List<ChatMessageDto>,
)

@Serializable
data class ChatDetail(
  val id: String,
  val title: String = "",
  @SerialName("created_at") val createdAt: String,
  @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class ChatMessageDto(
  val role: String,
  val content: String,
  @SerialName("created_at") val createdAt: String,
)


