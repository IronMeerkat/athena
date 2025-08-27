package nethical.digipaws.access

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent

class DigiPawsAccessibilityService : AccessibilityService() {
  override fun onAccessibilityEvent(event: AccessibilityEvent?) {
    // TODO: Hook into foreground app changes and URLs. Bridge via DevicePolicyClient.
  }

  override fun onInterrupt() {
  }
}


