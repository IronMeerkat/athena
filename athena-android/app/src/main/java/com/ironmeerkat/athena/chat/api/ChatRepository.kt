package com.ironmeerkat.athena.chat.api

import com.ironmeerkat.athena.chat.model.UiMessage
import kotlinx.coroutines.flow.Flow

interface ChatRepository {
  fun observeMessages(conversationId: String): Flow<List<UiMessage>>
  suspend fun sendMessage(conversationId: String, text: String)
}


