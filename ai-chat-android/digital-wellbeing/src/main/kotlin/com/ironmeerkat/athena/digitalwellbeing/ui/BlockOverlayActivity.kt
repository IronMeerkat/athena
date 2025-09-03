package com.ironmeerkat.athena.digitalwellbeing.ui

import androidx.activity.ComponentActivity
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Button
import androidx.core.view.setPadding
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import com.ironmeerkat.athena.digitalwellbeing.policy.PolicyDecision
import com.ironmeerkat.athena.digitalwellbeing.policy.PolicyEngine
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import timber.log.Timber

@AndroidEntryPoint
class BlockOverlayActivity : ComponentActivity() {

  @Inject lateinit var policyEngine: PolicyEngine

  private val job = Job()
  private val scope = CoroutineScope(Dispatchers.Main + job)

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    Timber.i("onCreate: showing block overlay")
    window.addFlags(
      WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
        WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD or
        WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
        WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
    )
    setContentView(buildContent())
  }

  private fun buildContent(): FrameLayout {
    val reason = intent.getStringExtra(EXTRA_REASON) ?: "Blocked"
    val target = intent.getStringExtra(EXTRA_TARGET) ?: ""
    Timber.d("buildContent: target=%s reason=%s", target, reason)
    val root = FrameLayout(this)
    val container = LinearLayout(this).apply {
      orientation = LinearLayout.VERTICAL
      setPadding(48)
    }
    val title = TextView(this).apply {
      text = "Blocked"
      textSize = 24f
    }
    val desc = TextView(this).apply {
      text = "$target\n$reason"
      textSize = 16f
    }
    val overrideBtn = Button(this).apply {
      text = "Override (5 min)"
      setOnClickListener {
        scope.launch {
          try {
            policyEngine.insertTemporaryWhitelist(target, 5)
            Timber.i("override: added temporary whitelist for %s", target)
          } catch (t: Throwable) {
            Timber.e(t, "override failed for %s", target)
          }
          finish()
        }
      }
    }
    container.addView(title)
    container.addView(desc)
    container.addView(overrideBtn)
    root.addView(container)
    return root
  }

  companion object {
    private const val EXTRA_REASON = "reason"
    private const val EXTRA_TARGET = "target"

    fun start(context: Context, decision: PolicyDecision) {
      val intent = Intent(context, BlockOverlayActivity::class.java).apply {
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        putExtra(EXTRA_REASON, when (decision) {
          is PolicyDecision.Allow -> decision.reason
          is PolicyDecision.Block -> decision.reason
        })
        putExtra(EXTRA_TARGET, "")
      }
      Timber.i("start: launching overlay for decision allow=%s", decision.allow)
      context.startActivity(intent)
    }
  }
}


