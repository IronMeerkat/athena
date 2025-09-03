package com.ironmeerkat.athena.digitalwellbeing.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import dagger.hilt.android.AndroidEntryPoint
import timber.log.Timber

@AndroidEntryPoint
class AppMonitorForegroundService : Service() {
  override fun onBind(intent: Intent?): IBinder? = null

  override fun onCreate() {
    super.onCreate()
    Timber.i("onCreate: starting foreground monitoring service")
    startForeground(1, buildNotification())
  }

  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    Timber.i("onStartCommand: action=%s flags=%d startId=%d", intent?.action, flags, startId)
    // Could manage periodic tasks if needed
    return START_STICKY
  }

  override fun onDestroy() {
    Timber.i("onDestroy: stopping foreground monitoring service")
    super.onDestroy()
  }

  private fun buildNotification(): Notification {
    val channelId = "digital_wellbeing_monitor"
    val mgr = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
      val channel = NotificationChannel(channelId, "Digital Wellbeing", NotificationManager.IMPORTANCE_LOW)
      mgr.createNotificationChannel(channel)
    }
    Timber.d("buildNotification: channelId=%s", channelId)
    return NotificationCompat.Builder(this, channelId)
      .setContentTitle("Digital Wellbeing active")
      .setContentText("Monitoring app/URL switches")
      .setSmallIcon(android.R.drawable.ic_secure)
      .build()
  }
}


