package com.ironmeerkat.athena.api.ws.subservices

import com.ironmeerkat.athena.api.ws.WebSocketSubservice
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/**
 * Journaling WS subservice, mounted at /ws/journal/{sessionId} on DRF.
 * Outgoing messages align with the working Jupyter example:
 * {"type":"message","user_message":"..."}
 */
class JournalWebSocketSubservice : WebSocketSubservice {
  override val name: String = "journal"

  override fun formatOutgoing(json: Json, userMessage: String): String {
    val obj: JsonObject = buildJsonObject {
      put("type", JsonPrimitive("message"))
      put("user_message", JsonPrimitive(userMessage))
    }
    return json.encodeToString(obj)
  }
}


