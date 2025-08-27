package com.ironmeerkat.athena.push

import android.app.PendingIntent
import android.content.Intent
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import nethical.digipaws.bridge.BlockerEvent
import nethical.digipaws.bridge.BlockerEvents
import com.ironmeerkat.athena.MainActivity
import com.ironmeerkat.athena.R
import com.ironmeerkat.athena.nav.NavRoutes

class AthenaMessagingService : FirebaseMessagingService() {
  override fun onNewToken(token: String) {
    super.onNewToken(token)
    // TODO: register token with DRF
  }

  override fun onMessageReceived(message: RemoteMessage) {
    super.onMessageReceived(message)
    val type = message.data["type"]
    when (type) {
      "nudge" -> {
        val ttl = message.data["ttl_minutes"]?.toIntOrNull() ?: 2
        val eventId = message.data["event_id"] ?: ""
        BlockerEvents.emit(BlockerEvent.Nudge(eventId, ttl))
        postNotification("Nudge available", "Accept $ttl min", NavRoutes.NUDGE)
      }
      "block" -> {
        val reason = message.data["reason"] ?: "Blocked"
        BlockerEvents.emit(BlockerEvent.Block(reason))
        postNotification("Blocked", reason, NavRoutes.BLOCK)
      }
    }
  }

  private fun postNotification(title: String, text: String, dest: String) {
    val intent = Intent(this, MainActivity::class.java).apply {
      putExtra("dest", dest)
      flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
    }
    val pi = PendingIntent.getActivity(this, dest.hashCode(), intent, PendingIntent.FLAG_IMMUTABLE)
    val builder = NotificationCompat.Builder(this, "athena_default")
      .setSmallIcon(R.drawable.ic_notification)
      .setContentTitle(title)
      .setContentText(text)
      .setContentIntent(pi)
      .setAutoCancel(true)
      .setPriority(NotificationCompat.PRIORITY_HIGH)
    NotificationManagerCompat.from(this).notify(dest.hashCode(), builder.build())
  }
}


