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

import com.google.firebase.database.DatabaseReference
import com.skydoves.firebase.database.ktx.flow
import com.ironmeerkat.athena.core.model.Channel
import com.ironmeerkat.athena.core.model.ChannelsSnapshot
import com.ironmeerkat.athena.core.model.Message
import kotlinx.coroutines.flow.Flow
import kotlinx.serialization.json.Json
import java.util.UUID
import javax.inject.Inject

internal class ChannelsRepositoryImpl @Inject constructor(
  private val databaseReference: DatabaseReference,
  private val json: Json,
) : ChannelsRepository {

  override fun fetchChannels(): Flow<Result<ChannelsSnapshot?>> {
    return databaseReference.flow(
      path = { snapshot -> snapshot },
      decodeProvider = { jsonString ->
        json.decodeFromString(jsonString)
      },
    )
  }

  override fun fetchChannel(index: Int): Flow<Result<Channel?>> {
    return databaseReference.flow(
      path = { snapshot -> snapshot.child("channels/$index") },
      decodeProvider = { jsonString ->
        json.decodeFromString(jsonString)
      },
    )
  }

  override fun addChannel(channels: List<Channel>) {
    val newChannels = channels + Channel(
      id = UUID.randomUUID().toString(),
      messages = listOf(Message.defaultMessage()),
    )

    databaseReference.child("channels").setValue(newChannels)
  }
}
