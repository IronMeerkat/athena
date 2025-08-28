package com.ironmeerkat.athena.chat.vm

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.ironmeerkat.athena.chat.api.ChatRepository
import com.ironmeerkat.athena.chat.impl.InMemoryChatRepository
import com.ironmeerkat.athena.chat.model.UiMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class ChatViewModel(private val repo: ChatRepository) : ViewModel() {
  private val conversationIdFlow = MutableStateFlow("default")

  val messages: StateFlow<List<UiMessage>> = conversationIdFlow
    .flatMapLatest { id -> repo.observeMessages(id) }
    .stateIn(scope = viewModelScope, started = SharingStarted.WhileSubscribed(5000), initialValue = emptyList())

  fun setConversation(id: String) {
    conversationIdFlow.value = id
  }

  fun send(text: String) {
    viewModelScope.launch { repo.sendMessage(conversationIdFlow.value, text) }
  }

  companion object {
    val factory: ViewModelProvider.Factory = viewModelFactory {
      initializer { ChatViewModel(InMemoryChatRepository()) }
    }
  }
}


