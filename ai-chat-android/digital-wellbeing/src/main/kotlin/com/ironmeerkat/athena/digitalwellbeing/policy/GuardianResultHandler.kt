package com.ironmeerkat.athena.digitalwellbeing.policy

import javax.inject.Inject
import javax.inject.Singleton
import org.json.JSONObject
import timber.log.Timber

@Singleton
class GuardianResultHandler @Inject constructor() {

  fun handleGuardianResult(resultJson: String) {
    try {
      val json = JSONObject(resultJson)
      val decision = json.optString("decision", json.optString("descision", "")).ifBlank { "unknown" }
      val title = json.optString("title", "")
      Timber.i("guardian result received: decision=%s title=%s", decision, title)
    } catch (t: Throwable) {
      Timber.e(t, "failed to handle guardian result")
    }
  }
}


