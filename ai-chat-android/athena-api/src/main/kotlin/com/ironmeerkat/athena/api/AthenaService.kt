package com.ironmeerkat.athena.api

import com.ironmeerkat.athena.api.dto.CreateRunRequest
import com.ironmeerkat.athena.api.dto.CreateRunResponse
import com.ironmeerkat.athena.api.dto.DeviceAttemptRequest
import com.ironmeerkat.athena.api.dto.DeviceAttemptResponse
import com.ironmeerkat.athena.api.dto.DevicePermitRequest
import com.ironmeerkat.athena.api.dto.DevicePermitResponse
import com.ironmeerkat.athena.api.dto.ChatsListResponse
import com.ironmeerkat.athena.api.dto.ChatMessagesResponse
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

/**
 * Retrofit interface for Athena DRF endpoints.
 *
 * This keeps the low-level HTTP layer small and type-safe. Higher-level
 * orchestration (like starting runs and streaming events) lives in
 * [AthenaClient].
 */
interface AthenaService {

  /** POST /api/runs/ — queue a new run on the server. */
  @POST("api/runs/")
  suspend fun createRun(
    @Body body: CreateRunRequest,
  ): CreateRunResponse

  /** POST /api/device/attempt — optional device flow helper. */
  @POST("api/device/attempt")
  suspend fun deviceAttempt(
    @Body body: DeviceAttemptRequest,
  ): DeviceAttemptResponse

  /** POST /api/device/permit — optional device flow helper. */
  @POST("api/device/permit")
  suspend fun devicePermit(
    @Body body: DevicePermitRequest,
  ): DevicePermitResponse

  /** GET /api/chats — list chats for the current user */
  @GET("api/chats")
  suspend fun getChats(): ChatsListResponse

  /** GET /api/chats/{chat_id}/messages — full message history */
  @GET("api/chats/{chat_id}/messages")
  suspend fun getChatMessages(
    @Path("chat_id") chatId: String,
  ): ChatMessagesResponse
}


