package com.ironmeerkat.athena.api.ws

import com.ironmeerkat.athena.api.di.AthenaBaseUrl
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import okhttp3.HttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response

/**
 * High-level WebSocket manager that opens a DRF WS for a given subservice
 * and streams human-readable text messages using the subservice's parser.
 */
class WebSocketService @Inject constructor(
  private val okHttp: OkHttpClient,
  @AthenaBaseUrl private val baseUrl: HttpUrl,
  private val json: Json,
) {

  fun open(
    subservice: WebSocketSubservice,
    sessionId: String,
    outgoingMessages: Flow<String>,
  ): Flow<String> = callbackFlow {
    val httpUrl = baseUrl.newBuilder()
      .addEncodedPathSegments("ws/${subservice.name}/$sessionId")
      .build()

    // OkHttp's HttpUrl only supports http/https schemes; for WebSocket use a String URL.
    val wsUrl = httpUrl.toString().replaceFirst("^http".toRegex(), "ws")

    val request = Request.Builder().url(wsUrl).build()
    val ws = okHttp.newWebSocket(request, object : okhttp3.WebSocketListener() {
      override fun onMessage(webSocket: okhttp3.WebSocket, text: String) {
        try {
          val parsed = subservice.parseIncoming(json, text)
          if (!parsed.isNullOrBlank()) trySend(parsed).isSuccess
        } catch (_: Throwable) {
          trySend(text).isSuccess
        }
      }

      override fun onClosed(webSocket: okhttp3.WebSocket, code: Int, reason: String) {
        close()
      }

      override fun onFailure(webSocket: okhttp3.WebSocket, t: Throwable, response: Response?) {
        close(t)
      }
    })

    val sendJob = launch {
      try {
        outgoingMessages.collect { msg ->
          if (msg.isNotBlank()) {
            val payload = try { subservice.formatOutgoing(json, msg) } catch (_: Throwable) { msg }
            ws.send(payload)
          }
        }
      } catch (_: Throwable) {
      }
    }

    awaitClose {
      try { ws.cancel() } catch (_: Throwable) {}
      try { sendJob.cancel() } catch (_: Throwable) {}
    }
  }
}


