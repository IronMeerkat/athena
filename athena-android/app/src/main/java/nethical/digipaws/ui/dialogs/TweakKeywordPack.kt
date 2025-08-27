package nethical.digipaws.ui.dialogs

import android.annotation.SuppressLint
import android.app.Dialog
import android.content.Context
import android.content.SharedPreferences
import android.os.Bundle
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import nethical.digipaws.R
import nethical.digipaws.databinding.DialogKeywordPackageBinding
import nethical.digipaws.services.KeywordBlockerService

class TweakKeywordPack : BaseDialog() {

    private lateinit var sharedPreferences: SharedPreferences

    @SuppressLint("ApplySharedPref")
    override fun onCreateDialog(savedInstanceState: Bundle?): Dialog {
        val dialogManageKeywordPacks = DialogKeywordPackageBinding.inflate(layoutInflater)

        // Initialize SharedPreferences
        sharedPreferences =
            requireContext().getSharedPreferences("keyword_blocker_packs", Context.MODE_PRIVATE)

        // Load current preferences into dialog
        dialogManageKeywordPacks.cbAdultKeywords.isChecked =
            sharedPreferences.getBoolean("adult_blocker", false)

        // Build and show the dialog
        return MaterialAlertDialogBuilder(requireContext())
            .setTitle(getString(R.string.manage_keyword_blockers))
            .setView(dialogManageKeywordPacks.root)
            .setCancelable(false)
            .setPositiveButton(getString(R.string.save)) { _, _ ->
                // Save changes to SharedPreferences
                with(sharedPreferences.edit()) {
                    putBoolean(
                        "adult_blocker",
                        dialogManageKeywordPacks.cbAdultKeywords.isChecked
                    )
                    commit() // Save changes immediately
                }

                // Send broadcast to refresh the KeywordBlockerService
                sendRefreshRequest(KeywordBlockerService.INTENT_ACTION_REFRESH_BLOCKED_KEYWORD_LIST)
            }
            .setNegativeButton(getString(R.string.cancel)) { dialog, _ ->
                dialog.dismiss()
            }
            .create()
    }

}
