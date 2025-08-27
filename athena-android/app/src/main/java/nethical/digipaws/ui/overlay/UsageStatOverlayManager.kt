package nethical.digipaws.ui.overlay

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.PixelFormat
import android.os.CountDownTimer
import android.util.Log
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.view.WindowManager.LayoutParams
import nethical.digipaws.databinding.OverlayUsageStatBinding

class UsageStatOverlayManager(private val context: Context) {

    private var overlayView: View? = null
    var binding: OverlayUsageStatBinding? = null
    var isOverlayVisible = false
    private var windowManager: WindowManager? = null

    var reelsScrolledThisSession = 0

    @SuppressLint("InlinedApi")
    fun startDisplaying() {
        if (overlayView != null || isOverlayVisible) return

        binding = OverlayUsageStatBinding.inflate(LayoutInflater.from(context))
        isOverlayVisible = true
        overlayView = binding?.root

        // Set up WindowManager.LayoutParams for the overlay
        val layoutParams = LayoutParams(
            LayoutParams.MATCH_PARENT,
            LayoutParams.MATCH_PARENT,
            LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            LayoutParams.FLAG_NOT_FOCUSABLE or
                    LayoutParams.FLAG_NOT_TOUCHABLE or
                    LayoutParams.FLAG_LAYOUT_IN_SCREEN
                    or LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        )
        layoutParams.gravity = Gravity.CENTER
        layoutParams.layoutInDisplayCutoutMode = LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES

        windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager

        windowManager?.addView(overlayView, layoutParams)
    }

    fun removeOverlay() {
        if (overlayView != null && windowManager != null) {
            Log.d("UsageStatOverlayManager", "Removing overlay.")
            windowManager?.removeView(overlayView)
            overlayView = null
            binding = null
            isOverlayVisible = false
        } else {
            Log.d("UsageStatOverlayManager", "No overlay to remove.")
        }
    }

}