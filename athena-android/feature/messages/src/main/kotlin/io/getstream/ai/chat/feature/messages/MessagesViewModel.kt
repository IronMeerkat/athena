/*
 * Designed and developed by 2024 skydoves (Jaewoong Eum)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.ironmeerkat.athena.feature.messages

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.ai.client.generativeai.Chat
import com.google.ai.client.generativeai.GenerativeModel
import com.google.ai.client.generativeai.type.Content
import com.google.ai.client.generativeai.type.TextPart
import com.google.ai.client.generativeai.type.asTextOrNull
import com.google.ai.client.generativeai.type.generationConfig
import dagger.assisted.Assisted
import dagger.assisted.AssistedFactory
import dagger.assisted.AssistedInject
import dagger.hilt.android.lifecycle.HiltViewModel
import com.ironmeerkat.athena.core.data.repository.ChannelsRepository
import com.ironmeerkat.athena.core.data.repository.MessagesRepository
import com.ironmeerkat.athena.core.model.Channel
import com.ironmeerkat.athena.core.model.Message
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.mapLatest
import kotlinx.coroutines.flow.stateIn

@HiltViewModel(assistedFactory = MessagesViewModel.Factory::class)
class MessagesViewModel @AssistedInject constructor(
  channelsRepository: ChannelsRepository,
  private val messagesRepository: MessagesRepository,
  @Assisted private val index: Int,
) : ViewModel() {

  val channelState: StateFlow<Channel?> = channelsRepository.fetchChannel(index)
    .mapLatest { result -> result.getOrNull() }
    .stateIn(
      scope = viewModelScope,
      started = SharingStarted.WhileSubscribed(5000),
      initialValue = null,
    )

  val messages: StateFlow<List<Message>> = channelState
    .mapLatest {
      it?.messages
    }.filterNotNull()
    .stateIn(
      scope = viewModelScope,
      started = SharingStarted.WhileSubscribed(5000),
      initialValue = emptyList(),
    )

  private val model = GenerativeModel(
    modelName = "gemini-pro",
    apiKey = BuildConfig.GEMINI_API_KEY,
    generationConfig = generationConfig {
      temperature = 0.5f
      candidateCount = 1
      maxOutputTokens = 1000
      topK = 30
      topP = 0.5f
    },
  )

  private val generativeChat: StateFlow<Chat> = messages.mapLatest { messageList ->
    model.startChat(
      history = messageList.map { singleMessage ->
        Content(
          parts = listOf(TextPart(singleMessage.message)),
        )
      },
    )
  }.stateIn(
    scope = viewModelScope,
    started = SharingStarted.WhileSubscribed(5000),
    initialValue = model.startChat(),
  )

  private val events: MutableStateFlow<MessagesEvent> = MutableStateFlow(MessagesEvent.Nothing)
  val latestResponse: StateFlow<String?> = events.flatMapLatest { event ->
    if (event is MessagesEvent.SendMessage) {
      generativeChat.value.sendMessageStream(event.message).map { it.text }
    } else {
      flowOf("")
    }
  }.stateIn(
    scope = viewModelScope,
    started = SharingStarted.WhileSubscribed(5000),
    initialValue = null,
  )

  fun isCompleted(text: String?): Boolean {
    return generativeChat.value.history.any { it.parts.any { it.asTextOrNull() == text } }
  }

  fun handleEvents(messagesEvent: MessagesEvent) {
    this.events.value = messagesEvent
    when (messagesEvent) {
      is MessagesEvent.SendMessage -> sendMessage(
        message = messagesEvent.message,
        sender = messagesEvent.sender,
      )

      is MessagesEvent.CompleteGeneration -> {
        sendMessage(
          message = messagesEvent.message,
          sender = messagesEvent.sender,
        )
      }

      is MessagesEvent.Nothing -> Unit
    }
  }

  private fun sendMessage(message: String, sender: String) {
    messagesRepository.sendMessage(
      index = index,
      channel = channelState.value!!,
      message = message,
      sender = sender,
    )
  }

  @AssistedFactory
  internal interface Factory {
    fun create(index: Int): MessagesViewModel
  }
}

sealed interface MessagesEvent {

  data object Nothing : MessagesEvent

  data class SendMessage(val message: String, val sender: String) : MessagesEvent

  data class CompleteGeneration(val message: String, val sender: String) : MessagesEvent
}
