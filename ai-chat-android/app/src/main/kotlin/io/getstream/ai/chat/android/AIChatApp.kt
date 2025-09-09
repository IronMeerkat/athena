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

import android.app.Application
import dagger.hilt.android.HiltAndroidApp
import io.getstream.log.AndroidStreamLogger
import io.getstream.log.StreamLog
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.ironmeerkat.athena.fcm.AthenaFirebaseMessagingService
import androidx.core.content.ContextCompat
import android.content.Intent
import com.ironmeerkat.athena.digitalwellbeing.service.AppMonitorForegroundService
import com.google.firebase.messaging.FirebaseMessaging
import dagger.hilt.android.EntryPointAccessors

@HiltAndroidApp
class AIChatApp : Application() {

  override fun onCreate() {
    super.onCreate()

    StreamLog.install(AndroidStreamLogger())

    // Ensure default notification channel exists for FCM notifications.
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
      val manager = getSystemService(NotificationManager::class.java)
      val channelId = AthenaFirebaseMessagingService.DEFAULT_CHANNEL_ID
      if (manager.getNotificationChannel(channelId) == null) {
        val channel = NotificationChannel(
          channelId,
          "Athena Notifications",
          NotificationManager.IMPORTANCE_DEFAULT
        )
        channel.description = "General updates from Athena"
        manager.createNotificationChannel(channel)
      }
    }

    // Start monitoring foreground service so activity is monitored even when app UI is not open
    try {
      val intent = Intent(this, AppMonitorForegroundService::class.java)
      ContextCompat.startForegroundService(this, intent)
    } catch (t: Throwable) {
      // Never swallow silently; always log
      StreamLog.getLogger("AIChatApp").e(t) { "Failed to start AppMonitorForegroundService at app start" }
    }

    // Ensure we have an up-to-date FCM token persisted
    FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
      if (task.isSuccessful) {
        val token = task.result
        if (!token.isNullOrBlank()) {
          val entryPoint = EntryPointAccessors.fromApplication(this, com.ironmeerkat.athena.di.AppEntryPoint::class.java)
          val store = entryPoint.pushTokenStore()
          kotlinx.coroutines.GlobalScope.launch(kotlinx.coroutines.Dispatchers.IO) { store.saveToken(token) }
        }
      } else {
        StreamLog.getLogger("AIChatApp").e(task.exception) { "Failed to get FCM token" }
      }
    }
  }
}
