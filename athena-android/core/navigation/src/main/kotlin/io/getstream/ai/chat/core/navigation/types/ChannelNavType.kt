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
package com.ironmeerkat.athena.core.navigation.types

import android.net.Uri
import android.os.Bundle
import androidx.navigation.NavType
import com.ironmeerkat.athena.core.model.Channel
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

object ChannelNavType : NavType<Channel?>(isNullableAllowed = true) {

  private val json = Json

  override fun get(bundle: Bundle, key: String): Channel? {
    val stringValue = bundle.getString(key) ?: return null
    val component = json.decodeFromString<Channel>(stringValue)
    return component
  }

  override fun put(bundle: Bundle, key: String, value: Channel?) {
    val stringValue = json.encodeToString(value)
    bundle.putSerializable(key, stringValue)
  }

  override fun serializeAsValue(value: Channel?): String {
    // Serialized values must always be Uri encoded
    return Uri.encode(Json.encodeToString(value))
  }

  override fun parseValue(value: String): Channel? {
    // Navigation takes care of decoding the string
    // before passing it to parseValue()
    return Json.decodeFromString<Channel?>(value)
  }
}
