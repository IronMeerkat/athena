package com.ironmeerkat.athena.fcm

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.ironmeerkat.athena.MainActivity
import com.ironmeerkat.athena.R

/**
 * Listens for Firebase Cloud Messaging events and surfaces them to the user.
 * - Logs new registration tokens.
 * - Handles data-only messages and shows a notification when appropriate.
 */
class AthenaFirebaseMessagingService : FirebaseMessagingService() {

  override fun onNewToken(token: String) {
    try {
      Log.i(TAG, "FCM new token: $token")
      // TODO: Optionally send token to backend for targeted notifications.
    } catch (t: Throwable) {
      Log.e(TAG, "Error handling new FCM token", t)
    }
  }

  override fun onMessageReceived(message: RemoteMessage) {
    try {
      val title = message.notification?.title
        ?: message.data["title"]
        ?: DEFAULT_TITLE
      val body = message.notification?.body
        ?: message.data["body"]
        ?: message.data["message"]
        ?: ""

      if (body.isNotBlank()) {
        showNotification(title, body)
      } else {
        Log.d(TAG, "Received FCM message with empty body; data=${message.data}")
      }
    } catch (t: Throwable) {
      Log.e(TAG, "Error handling FCM message", t)
    }
  }

  private fun showNotification(title: String, body: String) {
    try {
      ensureNotificationChannel()

      val intent = Intent(this, MainActivity::class.java).apply {
        addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_NEW_TASK)
      }
      val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
      val pendingIntent = PendingIntent.getActivity(this, 0, intent, flags)

      val notification = NotificationCompat.Builder(this, DEFAULT_CHANNEL_ID)
        .setSmallIcon(R.mipmap.ic_launcher)
        .setContentTitle(title)
        .setContentText(body)
        .setStyle(NotificationCompat.BigTextStyle().bigText(body))
        .setAutoCancel(true)
        .setContentIntent(pendingIntent)
        .build()

      with(NotificationManagerCompat.from(this)) {
        notify((System.currentTimeMillis() % Int.MAX_VALUE).toInt(), notification)
      }
    } catch (t: Throwable) {
      Log.e(TAG, "Failed to display notification", t)
    }
  }

  private fun ensureNotificationChannel() {
    if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
    try {
      val mgr = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
      val existing = mgr.getNotificationChannel(DEFAULT_CHANNEL_ID)
      if (existing == null) {
        val channel = android.app.NotificationChannel(
          DEFAULT_CHANNEL_ID,
          DEFAULT_CHANNEL_NAME,
          NotificationManager.IMPORTANCE_DEFAULT
        )
        channel.description = DEFAULT_CHANNEL_DESC
        mgr.createNotificationChannel(channel)
      }
    } catch (t: Throwable) {
      Log.e(TAG, "Error creating notification channel", t)
    }
  }

  companion object {
    private const val TAG = "AthenaFCM"
    private const val DEFAULT_TITLE = "Athena"
    const val DEFAULT_CHANNEL_ID = "athena_default"
    private const val DEFAULT_CHANNEL_NAME = "Athena Notifications"
    private const val DEFAULT_CHANNEL_DESC = "General updates from Athena"
  }
}


