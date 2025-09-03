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
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.mapLatest
import java.util.UUID
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import timber.log.Timber

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
  private val outgoingMessages: MutableSharedFlow<String> = MutableSharedFlow(extraBufferCapacity = 16)
  private val sessionId: String = UUID.randomUUID().toString()

  // Local buffer for messages when channelState is not yet available (new chat flow)
  private val _localMessages: MutableStateFlow<List<Message>> = MutableStateFlow(emptyList())
  val localMessages: StateFlow<List<Message>> = _localMessages
  val latestResponse: StateFlow<String?> = athenaClient
    .openJournalingWebSocket(sessionId = sessionId, outgoingMessages = outgoingMessages)
    .stateIn(
      scope = viewModelScope,
      started = SharingStarted.WhileSubscribed(5000),
      initialValue = null,
    )

  // Simple completion condition: when server indicates end by sending an empty chunk or UI decides.
  fun isCompleted(text: String?): Boolean = text.isNullOrEmpty()

  fun handleEvents(messagesEvent: MessagesEvent) {
    this.events.value = messagesEvent
    Timber.d("handleEvents: %s", messagesEvent)
    when (messagesEvent) {
      is ChatEvent.SendMessage -> sendMessage(
        message = messagesEvent.message,
        sender = messagesEvent.sender,
      )
        .also {
          // forward the raw text to the websocket
          outgoingMessages.tryEmit(messagesEvent.message)
          Timber.i("WS outgoing: %s session=%s", messagesEvent.message.take(64), sessionId)
        }

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
    Timber.d("sendMessage: sender=%s len=%d", sender, message.length)
    val currentChannel = channelState.value
    if (currentChannel == null) {
      // Append locally while server channel is not yet resolved
      _localMessages.value = _localMessages.value + Message(message = message, sender = sender)
      Timber.v("buffered local message; size=%d", _localMessages.value.size)
      return
    }

    try {
      messagesRepository.sendMessage(
        index = index,
        channel = currentChannel,
        message = message,
        sender = sender,
      )
      Timber.i("persisted message to channel index=%d", index)
    } catch (t: Throwable) {
      // Ensure we never swallow exceptions silently per user rule
      Timber.e(t, "Failed to persist message index=%d", index)
    }
  }

  @AssistedFactory
  internal interface Factory {
    fun create(index: Int): MessagesViewModel
  }
}

