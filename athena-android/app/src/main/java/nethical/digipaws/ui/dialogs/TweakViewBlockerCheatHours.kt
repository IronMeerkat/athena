package nethical.digipaws.ui.dialogs

import android.app.Dialog
import android.content.Context
import android.os.Bundle
import android.view.View
import android.widget.Toast
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import nethical.digipaws.R
import nethical.digipaws.databinding.DialogAddTimedActionBinding
import nethical.digipaws.services.ViewBlockerService
import nethical.digipaws.utils.SavedPreferencesLoader
import nl.joery.timerangepicker.TimeRangePicker

class TweakViewBlockerCheatHours(savedPreferencesLoader: SavedPreferencesLoader) : BaseDialog(
    savedPreferencesLoader
) {

    private var startTimeInMins: Int? = null
    private var endTimeInMins: Int? = null

    override fun onCreateDialog(savedInstanceState: Bundle?): Dialog {

        val dialogAddToCheatHoursBinding = DialogAddTimedActionBinding.inflate(layoutInflater)

        // Hide unused UI elements
        dialogAddToCheatHoursBinding.btnSelectUnblockedApps.visibility = View.GONE
        dialogAddToCheatHoursBinding.cheatHourTitle.visibility = View.GONE

        // Configure time picker
        dialogAddToCheatHoursBinding.picker.hourFormat = TimeRangePicker.HourFormat.FORMAT_24
        fixPickerInterceptBug(
            dialogAddToCheatHoursBinding.scrollview,
            dialogAddToCheatHoursBinding.picker
        )

        val viewBlockerCheatHours =
            requireContext().getSharedPreferences("cheat_hours", Context.MODE_PRIVATE)
        val savedEndTimeInMinutes = viewBlockerCheatHours.getInt("view_blocker_end_time", -1)
        val savedStartTimeInMinutes = viewBlockerCheatHours.getInt("view_blocker_start_time", -1)

        // Set saved times if available
        if (savedStartTimeInMinutes != -1 || savedEndTimeInMinutes != -1) {
            dialogAddToCheatHoursBinding.picker.startTimeMinutes = savedStartTimeInMinutes
            dialogAddToCheatHoursBinding.picker.endTimeMinutes = savedEndTimeInMinutes
            startTimeInMins = savedStartTimeInMinutes
            endTimeInMins = savedEndTimeInMinutes
        } else {
            dialogAddToCheatHoursBinding.picker.startTimeMinutes = 0
            dialogAddToCheatHoursBinding.picker.endTimeMinutes = 0
            dialogAddToCheatHoursBinding.fromTime.text = getString(R.string.from)
            dialogAddToCheatHoursBinding.endTime.text = getString(R.string.end)
        }

        // Handle time changes
        dialogAddToCheatHoursBinding.picker.setOnTimeChangeListener(object :
            TimeRangePicker.OnTimeChangeListener {
            override fun onStartTimeChange(startTime: TimeRangePicker.Time) {
                dialogAddToCheatHoursBinding.fromTime.text =
                    dialogAddToCheatHoursBinding.picker.startTime.toString()
                startTimeInMins = dialogAddToCheatHoursBinding.picker.startTimeMinutes
                endTimeInMins = dialogAddToCheatHoursBinding.picker.endTimeMinutes
            }

            override fun onEndTimeChange(endTime: TimeRangePicker.Time) {
                dialogAddToCheatHoursBinding.endTime.text =
                    dialogAddToCheatHoursBinding.picker.endTime.toString()
                startTimeInMins = dialogAddToCheatHoursBinding.picker.startTimeMinutes
                endTimeInMins = dialogAddToCheatHoursBinding.picker.endTimeMinutes
            }

            override fun onDurationChange(duration: TimeRangePicker.TimeDuration) {
                // No action needed
            }
        })

        // Show dialog
        return MaterialAlertDialogBuilder(requireContext())
            .setView(dialogAddToCheatHoursBinding.root)
            .setCancelable(false)
            .setPositiveButton(getString(R.string.save)) { dialog, _ ->
                if (startTimeInMins == null || endTimeInMins == null) {
                    Toast.makeText(
                        requireContext(),
                        getString(R.string.please_specify_time),
                        Toast.LENGTH_SHORT
                    ).show()
                    return@setPositiveButton
                }
                savedPreferencesLoader!!.saveCheatHoursForViewBlocker(
                    startTimeInMins!!,
                    endTimeInMins!!
                )
                sendRefreshRequest(ViewBlockerService.INTENT_ACTION_REFRESH_VIEW_BLOCKER)
                dialog.dismiss()
            }
            .setNegativeButton(getString(R.string.cancel)) { dialog, _ ->
                dialog.dismiss()
            }
            .create()
    }
}

