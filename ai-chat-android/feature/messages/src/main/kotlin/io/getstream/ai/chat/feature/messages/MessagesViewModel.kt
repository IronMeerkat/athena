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


import dagger.assisted.Assisted
import dagger.assisted.AssistedFactory
import dagger.assisted.AssistedInject
import dagger.hilt.android.lifecycle.HiltViewModel
import com.ironmeerkat.athena.core.data.repository.ChannelsRepository
import com.ironmeerkat.athena.core.data.repository.MessagesRepository
import com.ironmeerkat.athena.core.model.Channel
import com.ironmeerkat.athena.core.model.Message
import com.ironmeerkat.athena.api.AthenaClient
import com.ironmeerkat.athena.api.di.AthenaDefaultAgent
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.mapLatest
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

@OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
@HiltViewModel(assistedFactory = MessagesViewModel.Factory::class)
class MessagesViewModel @AssistedInject constructor(
  channelsRepository: ChannelsRepository,
  private val messagesRepository: MessagesRepository,
  private val athenaClient: AthenaClient,
  @AthenaDefaultAgent private val defaultAgent: String,
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

  private val events: MutableStateFlow<ChatEvent> = MutableStateFlow(ChatEvent.Nothing)
  val latestResponse: StateFlow<String?> = events
    .flatMapLatest { event ->
      if (event is ChatEvent.SendMessage) {
        // Build a minimal JSON input the server-side agent understands.
        val input = buildJsonObject {
          put("text", event.message)
          put("actor", "android")
        }
        // Stream from Athena as text chunks.
        athenaClient.streamText(
          agentId = defaultAgent,
          input = input,
          sensitive = false,
        )
      } else {
        flowOf("")
      }
    }
    .stateIn(
      scope = viewModelScope,
      started = SharingStarted.WhileSubscribed(5000),
      initialValue = null,
    )

  // Simple completion condition: when server indicates end by sending an empty chunk or UI decides.
  fun isCompleted(text: String?): Boolean = text.isNullOrEmpty()

  fun handleEvents(messagesEvent: MessagesEvent) {
    this.events.value = messagesEvent
    when (messagesEvent) {
      is ChatEvent.SendMessage -> sendMessage(
        message = messagesEvent.message,
        sender = messagesEvent.sender,
      )

      is ChatEvent.CompleteGeneration -> {
        sendMessage(
          message = messagesEvent.message,
          sender = messagesEvent.sender,
        )
      }

      is ChatEvent.Nothing -> Unit
      else -> Unit
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

