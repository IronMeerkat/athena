package com.ironmeerkat.athena.chat.vm

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.util.UUID

class ConversationsViewModel : ViewModel() {
  data class ConversationSummary(val id: String, val title: String)

  private val _conversations = MutableStateFlow<List<ConversationSummary>>(emptyList())
  val conversations: StateFlow<List<ConversationSummary>> = _conversations

  private val _activeId = MutableStateFlow("default")
  val activeId: StateFlow<String> = _activeId

  init {
    // Seed with a couple of conversations
    _conversations.value = listOf(
      ConversationSummary("default", "Today with Athena"),
      ConversationSummary(UUID.randomUUID().toString(), "Weekly planning"),
      ConversationSummary(UUID.randomUUID().toString(), "Focus session")
    )
  }

  fun select(id: String) {
    _activeId.value = id
  }

  fun newConversation(title: String) {
    viewModelScope.launch {
      val id = UUID.randomUUID().toString()
      _conversations.value = _conversations.value + ConversationSummary(id, title)
      _activeId.value = id
    }
  }

  companion object {
    val factory: ViewModelProvider.Factory = viewModelFactory {
      initializer { ConversationsViewModel() }
    }
  }
}
