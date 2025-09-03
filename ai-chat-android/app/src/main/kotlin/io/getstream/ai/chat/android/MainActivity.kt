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
package com.ironmeerkat.athena

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import dagger.hilt.android.AndroidEntryPoint
import com.ironmeerkat.athena.navigation.AIChatNavHost
import com.ironmeerkat.athena.core.designsystem.theme.AIChatTheme
import com.ironmeerkat.athena.core.navigation.AIChatScreen
import com.ironmeerkat.athena.core.navigation.AppComposeNavigator
import com.ironmeerkat.athena.core.navigation.LocalComposeNavigator
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

  @Inject
  lateinit var composeNavigator: AppComposeNavigator<AIChatScreen>

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)

    setContent {
      CompositionLocalProvider(
        LocalComposeNavigator provides composeNavigator,
      ) {
        AIChatTheme {
          val gate: AuthGateViewModel = androidx.hilt.navigation.compose.hiltViewModel()
          val loggedIn by gate.isLoggedIn.collectAsState()
          val start = if (loggedIn) AIChatScreen.Channels else AIChatScreen.Login
          AIChatNavHost(composeNavigator = composeNavigator, startDestination = start)
        }
      }
    }
  }
}
