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
package com.ironmeerkat.athena.core.navigation

import androidx.compose.runtime.Immutable
import androidx.compose.runtime.Stable
import androidx.navigation.NavType
import com.ironmeerkat.athena.core.model.Channel
import com.ironmeerkat.athena.core.navigation.types.ChannelNavType
import kotlinx.serialization.Serializable
import kotlin.reflect.typeOf

@Stable
sealed interface AIChatScreen {

  @Immutable
  @Serializable
  data object Channels : AIChatScreen

  @Immutable
  @Serializable
  data class Messages(val index: Int, val channel: Channel) : AIChatScreen {

    companion object {
      val typeMap = mapOf(typeOf<Int>() to NavType.IntType, typeOf<Channel>() to ChannelNavType)
    }
  }
}
