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
package com.ironmeerkat.athena.feature.channels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import com.ironmeerkat.athena.core.data.repository.ChannelsRepository
import com.ironmeerkat.athena.core.model.Channel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.mapLatest
import kotlinx.coroutines.flow.stateIn
import javax.inject.Inject

@HiltViewModel
class ChannelsViewModel @Inject constructor(
  private val channelsRepository: ChannelsRepository,
) : ViewModel() {

  val channels: StateFlow<List<Channel>> = channelsRepository.fetchChannels()
    .mapLatest { result -> result.getOrNull() }
    .filterNotNull()
    .map { snapshot -> snapshot.channels }
    .stateIn(
      scope = viewModelScope,
      started = SharingStarted.WhileSubscribed(5000),
      initialValue = emptyList(),
    )

  fun handleEvents(channelsEvent: ChannelsEvent) {
    when (channelsEvent) {
      is ChannelsEvent.CreateChannel -> channelsRepository.addChannel(channels.value)
    }
  }
}

sealed interface ChannelsEvent {

  data object CreateChannel : ChannelsEvent
}
