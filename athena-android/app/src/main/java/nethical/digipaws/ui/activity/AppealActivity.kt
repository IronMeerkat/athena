package nethical.digipaws.ui.activity

import android.os.Bundle
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.NumberPicker
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import nethical.digipaws.net.ServerClient
import nethical.digipaws.services.AppBlockerService

/**
 * Minimal appeals flow. Expects extras: packageName (String)
 */
class AppealActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val entityType = intent.getStringExtra("entity_type") ?: "app"
        val pkg = intent.getStringExtra("packageName")
        val keyword = intent.getStringExtra("keyword")
        if (entityType == "app" && pkg == null) { finish(); return }
        if (entityType == "keyword" && keyword == null) { finish(); return }

        val input = EditText(this).apply {
            hint = "Briefly justify why you need access now"
        }
        val minutesPicker = NumberPicker(this).apply {
            minValue = 1
            maxValue = 15
            value = 3
        }
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val pad = (16 * resources.displayMetrics.density).toInt()
            setPadding(pad, pad, pad, pad)
            addView(input)
            addView(minutesPicker)
        }

        val server = ServerClient(this)

        MaterialAlertDialogBuilder(this)
            .setTitle("Appeal Access")
            .setMessage("Explain your reason and choose minimal minutes.")
            .setView(container)
            .setPositiveButton("Submit") { dialog, _ ->
                val minutes = minutesPicker.value
                val justification = input.text?.toString() ?: ""
                // For MVP, accept all appeals up to requested minutes; future: call server
                val recommended = minutes
                if (recommended > 0) {
                    Toast.makeText(this, "Appeal accepted: ${recommended} min", Toast.LENGTH_SHORT).show()
                    val durationMs = recommended * 60_000
                    if (entityType == "app" && pkg != null) {
                        // App: use cooldown to temporarily whitelist
                        val b = android.content.Intent(AppBlockerService.INTENT_ACTION_REFRESH_APP_BLOCKER_COOLDOWN).apply {
                            putExtra("result_id", pkg)
                            putExtra("selected_time", durationMs)
                        }
                        sendBroadcast(b)
                    } else if (entityType == "keyword" && keyword != null) {
                        val kbWhitelistIntent = android.content.Intent(nethical.digipaws.services.KeywordBlockerService.INTENT_ACTION_TEMP_WHITELIST_KEYWORD).apply {
                            putExtra("keyword", keyword)
                            putExtra("selected_time", durationMs)
                        }
                        sendBroadcast(kbWhitelistIntent)
                    }
                    setResult(RESULT_OK, intent)
                } else {
                    Toast.makeText(this, "Appeal rejected", Toast.LENGTH_SHORT).show()
                    setResult(RESULT_CANCELED, intent)
                }
                dialog.dismiss()
                finish()
            }
            .setNegativeButton("Cancel") { dialog, _ ->
                dialog.dismiss()
                setResult(RESULT_CANCELED, intent)
                finish()
            }
            .setCancelable(false)
            .show()
    }
}


