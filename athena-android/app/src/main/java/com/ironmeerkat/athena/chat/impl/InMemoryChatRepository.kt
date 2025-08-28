package com.ironmeerkat.athena.chat.impl

import com.ironmeerkat.athena.chat.api.ChatRepository
import com.ironmeerkat.athena.chat.model.Sender
import com.ironmeerkat.athena.chat.model.UiMessage
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.UUID

class InMemoryChatRepository : ChatRepository {
  private val convoToMessages = mutableMapOf<String, MutableStateFlow<List<UiMessage>>>()

  override fun observeMessages(conversationId: String): Flow<List<UiMessage>> {
    val flow = convoToMessages.getOrPut(conversationId) { MutableStateFlow(seed(conversationId)) }
    return flow.asStateFlow()
  }

  override suspend fun sendMessage(conversationId: String, text: String) {
    val flow = convoToMessages.getOrPut(conversationId) { MutableStateFlow(seed(conversationId)) }
    val userMsg = UiMessage(
      id = UUID.randomUUID().toString(),
      sender = Sender.USER,
      text = text,
      timestampMs = System.currentTimeMillis()
    )
    flow.value = flow.value + userMsg
    // Simulate assistant response
    delay(400)
    val assistant = UiMessage(
      id = UUID.randomUUID().toString(),
      sender = Sender.ASSISTANT,
      text = "You said: \"$text\"",
      timestampMs = System.currentTimeMillis()
    )
    flow.value = flow.value + assistant
  }

  private fun seed(conversationId: String): List<UiMessage> = listOf(
    UiMessage(
      id = UUID.randomUUID().toString(),
      sender = Sender.ASSISTANT,
      text = "Welcome to Athena chat.",
      timestampMs = System.currentTimeMillis() - 60_000
    )
  )
}


