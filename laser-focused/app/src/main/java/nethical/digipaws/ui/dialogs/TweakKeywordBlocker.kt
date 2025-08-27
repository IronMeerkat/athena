package nethical.digipaws.ui.dialogs

import android.annotation.SuppressLint
import android.app.Dialog
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Bundle
import android.view.View
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity.RESULT_OK
import androidx.core.app.ActivityOptionsCompat
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import nethical.digipaws.R
import nethical.digipaws.databinding.DialogKeywordBlockerConfigBinding
import nethical.digipaws.services.KeywordBlockerService
import nethical.digipaws.ui.activity.SelectAppsActivity
import nethical.digipaws.utils.SavedPreferencesLoader

class TweakKeywordBlocker(savedPreferencesLoader: SavedPreferencesLoader) :
    BaseDialog(savedPreferencesLoader) {

    private lateinit var sharedPreferences: SharedPreferences

    private var ignoredAppsSize = 0

    @SuppressLint("ApplySharedPref", "SetTextI18n")
    override fun onCreateDialog(savedInstanceState: Bundle?): Dialog {
        val dialogManageKeywordBlocker = DialogKeywordBlockerConfigBinding.inflate(layoutInflater)


        val selectIgnoredApps: ActivityResultLauncher<Intent> =
            registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
                if (result.resultCode == RESULT_OK) {
                    val selectedApps = result.data?.getStringArrayListExtra("SELECTED_APPS")
                    selectedApps?.let {
                        ignoredAppsSize = selectedApps.size
                        dialogManageKeywordBlocker.ignoredKbApps.setText(dialogManageKeywordBlocker.ignoredKbApps.text.toString() + " " + "($ignoredAppsSize)")
                        savedPreferencesLoader?.saveKeywordBlockerIgnoredApps(selectedApps)
                    }
                }
            }
        if (!dialogManageKeywordBlocker.cbSearchTextField.isChecked) {
            dialogManageKeywordBlocker.ignoredKbApps.visibility = View.GONE
        }
        dialogManageKeywordBlocker.cbSearchTextField.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked) {
                dialogManageKeywordBlocker.ignoredKbApps.visibility = View.VISIBLE
            } else {
                dialogManageKeywordBlocker.ignoredKbApps.visibility = View.GONE
            }
        }

        dialogManageKeywordBlocker.ignoredKbApps.setOnClickListener {

            val intent = Intent(requireContext(), SelectAppsActivity::class.java)
            intent.putStringArrayListExtra(
                "PRE_SELECTED_APPS",
                ArrayList(savedPreferencesLoader?.getKeywordBlockerIgnoredApps() ?: emptyList())
            )
            selectIgnoredApps.launch(
                intent,
                ActivityOptionsCompat.makeCustomAnimation(
                    requireContext(),
                    R.anim.fade_in,
                    R.anim.fade_out
                )
            )
        }

        // Initialize SharedPreferences
        sharedPreferences =
            requireContext().getSharedPreferences("keyword_blocker_configs", Context.MODE_PRIVATE)

        // Load current preferences into dialog
        dialogManageKeywordBlocker.cbSearchTextField.isChecked =
            sharedPreferences.getBoolean("search_all_text_fields", false)
        dialogManageKeywordBlocker.redirectUrl.setText(
            sharedPreferences.getString(
                "redirect_url",
                "https://www.youtube.com/watch?v=x31tDT-4fQw&t=1s"
            )
        )

        // Build and show the dialog
        return MaterialAlertDialogBuilder(requireContext())
            .setView(dialogManageKeywordBlocker.root)
            .setCancelable(false)
            .setPositiveButton(getString(R.string.ok)) { _, _ ->
                // Save changes to SharedPreferences
                with(sharedPreferences.edit()) {
                    putBoolean(
                        "search_all_text_fields",
                        dialogManageKeywordBlocker.cbSearchTextField.isChecked
                    )
                    putString(
                        "redirect_url",
                        dialogManageKeywordBlocker.redirectUrl.text.toString()
                    )
                    commit() // Save changes immediately
                }

                // Send broadcast to refresh the KeywordBlockerService
                sendRefreshRequest(KeywordBlockerService.INTENT_ACTION_REFRESH_CONFIG)
            }
            .setNegativeButton(getString(R.string.close)) { _, _ ->
                // Do nothing on cancel
            }
            .create()
    }

}
