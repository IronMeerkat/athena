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
package com.ironmeerkat.athena.core.data.repository

import com.ironmeerkat.athena.api.AthenaService
import com.ironmeerkat.athena.api.dto.ChatMessageDto
import com.ironmeerkat.athena.core.model.Channel
import com.ironmeerkat.athena.core.model.ChannelsSnapshot
import com.ironmeerkat.athena.core.model.Message
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

internal class ChannelsRepositoryImpl @Inject constructor(
  private val service: AthenaService,
) : ChannelsRepository {

  override fun fetchChannels(): Flow<Result<ChannelsSnapshot?>> = flow {
    try {
      val resp = service.getChats()
      val channels: List<Channel> = resp.chats.map { summary ->
        val msgs: List<Message> = summary.lastMessage?.let { listOf(it.toUiMessage()) } ?: emptyList()
        Channel(id = summary.id, messages = msgs)
      }
      emit(Result.success(ChannelsSnapshot(channels)))
    } catch (t: Throwable) {
      emit(Result.failure(t))
    }
  }

  override fun fetchChannel(index: Int): Flow<Result<Channel?>> = flow {
    try {
      val chats = service.getChats().chats
      if (index < 0 || index >= chats.size) {
        emit(Result.success(null))
        return@flow
      }
      val summary = chats[index]
      val history = service.getChatMessages(summary.id)
      val messages = history.messages.map { it.toUiMessage() }
      emit(Result.success(Channel(id = summary.id, messages = messages)))
    } catch (t: Throwable) {
      emit(Result.failure(t))
    }
  }

  override fun addChannel(channels: List<Channel>) {
    // No-op for now; server creates chats implicitly on WS connect.
  }
}

private fun ChatMessageDto.toUiMessage(): Message =
  Message(
    sender = if (role.equals("assistant", ignoreCase = true)) "AI" else "User",
    message = content,
  )
