package nethical.digipaws

import android.app.Application
import com.google.android.material.color.DynamicColors
import nethical.digipaws.utils.SavedPreferencesLoader

class Digipaws: Application() {
  override fun onCreate() {
    DynamicColors.applyToActivitiesIfAvailable(this)
    Thread.setDefaultUncaughtExceptionHandler(CrashLogger(this))
    super.onCreate()
  }

  // Agentic features purged
}
