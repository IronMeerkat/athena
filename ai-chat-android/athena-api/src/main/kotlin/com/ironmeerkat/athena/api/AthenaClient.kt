package com.ironmeerkat.athena.api

import com.ironmeerkat.athena.api.dto.CreateRunRequest
import com.ironmeerkat.athena.api.dto.CreateRunResponse
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import okhttp3.HttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Call
import okhttp3.Callback
import okhttp3.Response
import okio.BufferedSource

/**
 * AthenaClient is a small, high-level facade that:
 * 1) Creates a run via POST /api/runs.
 * 2) Connects to Server-Sent Events (SSE) at /api/runs/{id}/events.
 * 3) Streams text chunks as a Flow<String> you can collect in the UI.
 *
 * It's intentionally minimal and easy to extend when you add new agents.
 */
class AthenaClient @Inject constructor(
  private val service: AthenaService,
  private val okHttp: OkHttpClient,
  private val baseUrl: HttpUrl,
  private val json: Json,
) {

  /** Starts a run and returns the new run ID. */
  private suspend fun createRun(
    agentId: String,
    input: JsonElement,
    sensitive: Boolean,
  ): CreateRunResponse {
    val options = buildMap<String, JsonElement> {
      put("sensitive", JsonPrimitive(sensitive))
      put("stream", JsonPrimitive(true))
    }
    return service.createRun(CreateRunRequest(agentId = agentId, input = input, options = options))
  }

  /**
   * Starts a run, then opens the SSE stream and emits text chunks as they arrive.
   *
   * - agentId: which agent to run on the server side (e.g., "guardian").
   * - input: arbitrary JSON you want to send to the agent.
   * - sensitive: route to the sensitive queue if true.
   */
  fun streamText(
    agentId: String,
    input: JsonElement,
    sensitive: Boolean,
  ): Flow<String> = callbackFlow {
    // Create the run first.
    val run = try {
      createRun(agentId, input, sensitive)
    } catch (t: Throwable) {
      close(t)
      return@callbackFlow
    }

    // Build the SSE GET request.
    val url = baseUrl.newBuilder()
      .addEncodedPathSegments("api/runs/${run.runId}/events")
      .build()
    val request = Request.Builder()
      .url(url)
      .get()
      .header("Accept", "text/event-stream")
      .build()

    val call = okHttp.newCall(request)
    call.enqueue(object : Callback {
      override fun onFailure(call: Call, e: java.io.IOException) {
        close(e)
      }

      override fun onResponse(call: Call, response: Response) {
        if (!response.isSuccessful) {
          close(IllegalStateException("SSE connection failed: ${response.code}"))
          response.close()
          return
        }
        val source: BufferedSource = response.body!!.source()
        try {
          val dataBuffer = mutableListOf<String>()
          while (!isClosedForSend) {
            val line = source.readUtf8Line() ?: break
            if (line.isEmpty()) {
              if (dataBuffer.isNotEmpty()) {
                val payload = dataBuffer.joinToString("\n")
                  .removePrefix("data: ")
                emitTextChunk(payload)
                dataBuffer.clear()
              }
              continue
            }
            if (line.startsWith(":")) continue
            if (line.startsWith("data:")) {
              dataBuffer += line.removePrefix("data:").trimStart()
            }
          }
        } catch (t: Throwable) {
          if (t is CancellationException) return
        } finally {
          response.close()
          close()
        }
      }
    })

    awaitClose {
      try { call.cancel() } catch (_: Throwable) {}
    }
  }

  /**
   * Tries to parse a JSON object and extract a human-readable text field.
   * Falls back to emitting the raw string if structure is unknown.
   */
  private fun kotlinx.coroutines.channels.ProducerScope<String>.emitTextChunk(raw: String) {
    val trimmed = raw.trim()
    if (trimmed.isEmpty() || trimmed == "{}") return
    val element = try {
      json.parseToJsonElement(trimmed)
    } catch (_: Throwable) {
      null
    }
    when (element) {
      is JsonObject -> {
        // Common field names you might use server-side for streaming tokens.
        val candidates = listOf("text", "delta", "content", "message")
        val text = candidates.asSequence()
          .mapNotNull { key -> (element[key] as? JsonPrimitive)?.contentOrNull }
          .firstOrNull()
        trySend(text ?: element.toString()).isSuccess
      }
      is JsonElement -> {
        trySend(element.toString()).isSuccess
      }
      else -> {
        trySend(trimmed).isSuccess
      }
    }
  }
}


