package com.ironmeerkat.athena.digitalwellbeing.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat
import com.ironmeerkat.athena.digitalwellbeing.service.AppMonitorForegroundService
import timber.log.Timber

class BootCompletedReceiver : BroadcastReceiver() {
  override fun onReceive(context: Context, intent: Intent) {
    val action = intent.action
    Timber.i("BootCompletedReceiver.onReceive action=%s", action)
    try {
      val serviceIntent = Intent(context, AppMonitorForegroundService::class.java)
      ContextCompat.startForegroundService(context, serviceIntent)
    } catch (t: Throwable) {
      Timber.e(t, "Failed to start AppMonitorForegroundService from BootCompletedReceiver")
    }
  }
}


