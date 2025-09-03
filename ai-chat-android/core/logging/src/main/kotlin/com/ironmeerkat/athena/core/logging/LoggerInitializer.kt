package com.ironmeerkat.athena.core.logging

import android.content.Context
import androidx.startup.Initializer
import timber.log.Timber
import com.ironmeerkat.athena.core.logging.BuildConfig

/**
 * Initializes Timber with a module-tagged tree on app start.
 */
class LoggerInitializer : Initializer<Unit> {
  override fun create(context: Context) {
    if (BuildConfig.DEBUG) {
      Timber.plant(ModuleTaggedDebugTree())
    } else {
      Timber.plant(ReleaseTree())
    }
  }

  override fun dependencies(): MutableList<Class<out Initializer<*>>> = mutableListOf()
}


