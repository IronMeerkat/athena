package com.ironmeerkat.athena.core.logging

import android.util.Log
import timber.log.Timber

/**
 * A release tree that only logs WARN and above to Logcat. Errors always logged.
 */
internal class ReleaseTree : Timber.Tree() {
  override fun isLoggable(tag: String?, priority: Int): Boolean {
    return priority >= Log.WARN
  }

  override fun log(priority: Int, tag: String?, message: String, t: Throwable?) {
    if (!isLoggable(tag, priority)) return
    if (t != null) {
      Log.println(priority, tag, message + "\n" + Log.getStackTraceString(t))
    } else {
      Log.println(priority, tag, message)
    }
  }
}


