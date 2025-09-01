package com.ironmeerkat.athena.api.ws

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

/**
 * Describes a DRF WebSocket subservice mounted under /ws/{name}/{sessionId}.
 * Implementations provide simple parsing/formatting so the UI can just work
 * with human-readable strings while server messages can stay structured JSON.
 */
interface WebSocketSubservice {
  /** Path segment after /ws/, e.g., "journal". */
  val name: String

  /**
   * Parses an incoming raw WebSocket message into a human-readable text.
   * Return null if the message should be ignored by the high-level stream.
   */
  fun parseIncoming(json: Json, raw: String): String? {
    val trimmed = raw.trim()
    if (trimmed.isEmpty()) return null
    val element = try {
      json.parseToJsonElement(trimmed)
    } catch (_: Throwable) {
      null
    }
    when (element) {
      is JsonObject -> {
        // Prefer nested data.text, but fall back to common field names.
        val data = element["data"] as? JsonObject
        val candidates = listOf("text", "delta", "content", "message", "assistant")
        val fromData = data?.let { obj ->
          candidates.asSequence()
            .mapNotNull { key -> (obj[key] as? JsonPrimitive)?.contentOrNull }
            .firstOrNull()
        }
        if (!fromData.isNullOrBlank()) return fromData

        val fromTop = candidates.asSequence()
          .mapNotNull { key -> (element[key] as? JsonPrimitive)?.contentOrNull }
          .firstOrNull()
        if (!fromTop.isNullOrBlank()) return fromTop

        return element.toString()
      }
      is JsonElement -> return element.toString()
      else -> return trimmed
    }
  }

  /**
   * Formats an outgoing user message to the server. Default passes through raw text.
   * Subservices may override to build JSON envelopes the server expects.
   */
  fun formatOutgoing(json: Json, userMessage: String): String = userMessage
}


