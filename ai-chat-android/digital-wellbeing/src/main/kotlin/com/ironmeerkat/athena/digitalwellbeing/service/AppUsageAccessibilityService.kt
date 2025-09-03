package com.ironmeerkat.athena.digitalwellbeing.service

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import com.ironmeerkat.athena.digitalwellbeing.policy.PolicyEngine
import com.ironmeerkat.athena.digitalwellbeing.policy.Target
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import timber.log.Timber

import com.ironmeerkat.athena.digitalwellbeing.ui.BlockOverlayActivity

@AndroidEntryPoint
class AppUsageAccessibilityService : AccessibilityService() {

  @Inject lateinit var policyEngine: PolicyEngine

  private val serviceJob = Job()
  private val scope = CoroutineScope(Dispatchers.Main + serviceJob)

  override fun onAccessibilityEvent(event: AccessibilityEvent?) {
    if (event == null) return
    if (
      event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED ||
      event.eventType == AccessibilityEvent.TYPE_WINDOWS_CHANGED ||
      event.eventType == AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED ||
      event.eventType == AccessibilityEvent.TYPE_VIEW_FOCUSED ||
      event.eventType == AccessibilityEvent.TYPE_VIEW_CLICKED
    ) {
      val pkg = event.packageName?.toString()
      val url = extractUrlFromEvent(event)
      val target = Target(appPackage = pkg, url = url)
      Timber.d("onAccessibilityEvent: type=%d pkg=%s url=%s", event.eventType, pkg, url)
      scope.launch {
        try {
          val decision = policyEngine.onTargetChanged(target)
          Timber.i("decision: allow=%s reason=%s target=%s", decision.allow, when (decision) {
            is com.ironmeerkat.athena.digitalwellbeing.policy.PolicyDecision.Allow -> decision.reason
            is com.ironmeerkat.athena.digitalwellbeing.policy.PolicyDecision.Block -> decision.reason
          }, target)
          if (!decision.allow) {
            BlockOverlayActivity.start(this@AppUsageAccessibilityService, decision)
          }
        } catch (t: Throwable) {
          Timber.e(t, "policyEngine.onTargetChanged failed")
        }
      }
    }
  }

  override fun onServiceConnected() {
    super.onServiceConnected()
    Timber.i("onServiceConnected: accessibility service bound and active")
  }

  override fun onInterrupt() {}

  private fun extractUrlFromEvent(event: AccessibilityEvent): String? {
    // Best-effort: try content descriptions or text nodes
    val texts = event.text?.joinToString(" ") ?: return null
    val regex = Regex("https?://\\S+")
    return regex.find(texts)?.value
  }
}


