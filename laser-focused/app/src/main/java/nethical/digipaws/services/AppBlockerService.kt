package nethical.digipaws.services

import android.annotation.SuppressLint
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.widget.Toast
import nethical.digipaws.Constants
import nethical.digipaws.blockers.AppBlocker
import nethical.digipaws.blockers.FocusModeBlocker
import nethical.digipaws.net.ServerClient
import nethical.digipaws.ui.activity.MainActivity
import nethical.digipaws.ui.activity.WarningActivity
import nethical.digipaws.ui.activity.AppealActivity
import nethical.digipaws.utils.getCurrentKeyboardPackageName
import nethical.digipaws.utils.getDefaultLauncherPackageName
import nethical.digipaws.utils.GeoTools
import nethical.digipaws.utils.PointOfInterest
import nethical.digipaws.utils.GeoBlockPolicy

class AppBlockerService : BaseBlockingService() {

    companion object {
        /**
         * Refreshes information about warning screen, cheat hours and blocked app list
         */
        const val INTENT_ACTION_REFRESH_APP_BLOCKER = "nethical.digipaws.refresh.appblocker"

        /**
         * Add cooldown to an app.
         * This broadcast should always be sent together with the following keys:
         * selected_time: Int -> Duration of cooldown in minutes
         * result_id : String -> Package name of app to be put into cooldown
         */
        const val INTENT_ACTION_REFRESH_APP_BLOCKER_COOLDOWN =
            "nethical.digipaws.refresh.appblocker.cooldown"

        /**
         * Refreshes information related to focus mode.
         */

        const val INTENT_ACTION_REFRESH_FOCUS_MODE = "nethical.digipaws.refresh.focus_mode"
    }

    private var appBlockerWarning = MainActivity.WarningData()
    private val appBlocker = AppBlocker()

    private val focusModeBlocker = FocusModeBlocker()
    private val serverClient by lazy { ServerClient(this) }

    // responsible to trigger a recheck for what app user is currently using even when no event is received. Used in putting the usage recheck logic into
    // cooldown for an app and later when the cooldown duration is over, trigger a recheck
    private val handler = Handler(Looper.getMainLooper())


    private var updateRunnable: Runnable? = null



    private var lastPackage = ""

    private var pointsOfInterest: List<PointOfInterest> = emptyList()
    private var geoPolicies: List<GeoBlockPolicy> = emptyList()
    private var lastKnownLat: Double? = null
    private var lastKnownLon: Double? = null

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val packageName = event?.packageName.toString()
        if (lastPackage == packageName || packageName == getPackageName()) return

        lastPackage = packageName
        Log.d("AppBlockerService", "Switched to app $packageName")

        val focusModeResult = focusModeBlocker.doesAppNeedToBeBlocked(packageName)
        if (focusModeResult.isBlocked) {
            handleFocusModeBlockerResult(focusModeResult)
            return
        }
        // Geo enforcement: block if current app matches a policy and inside POI within time window
        if (isBlockedByGeoPolicy(packageName)) {
            handleAppBlockerResult(AppBlocker.AppBlockerResult(true), packageName)
            return
        }
        val appBlockerResult = appBlocker.doesAppNeedToBeBlocked(packageName)
        if (appBlockerResult.isBlocked || appBlockerResult.cheatHoursEndTime != -1L || appBlockerResult.cooldownEndTime != -1L) {
            handleAppBlockerResult(appBlockerResult, packageName)
            return
        }
        // Server decision for uncategorized apps when within schedule
        if (!nethical.digipaws.utils.ScheduleUtils.isWithinScheduleNow(this)) return
        val activityName = try { rootInActiveWindow?.className?.toString() } catch (_: Exception) { null }
        val serverDecision = serverClient.classifyApp(packageName, activityName) ?: return
        if (serverDecision.shouldBlock) {
            // Prompt appeal UI
            pressHome()
            Thread.sleep(200)
            val intent = Intent(this, AppealActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
                putExtra("entity_type", "app")
                putExtra("packageName", packageName)
            }
            startActivity(intent)
        } else {
            return
        }
    }


    private fun handleAppBlockerResult(result: AppBlocker.AppBlockerResult, packageName: String) {
        Log.d("AppBlockerService", "$packageName result : $result")

        if (result.cheatHoursEndTime != -1L) {
            setUpForcedRefreshChecker(packageName, result.cheatHoursEndTime)
        }
        if (result.cooldownEndTime != -1L) {
            setUpForcedRefreshChecker(packageName, result.cooldownEndTime)
        }

        if (!result.isBlocked) return


        if (appBlockerWarning.isWarningDialogHidden) {
            pressHome()
            return
        }

        pressHome()
        Thread.sleep(300)
        val dialogIntent = Intent(this, WarningActivity::class.java)
        dialogIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
        dialogIntent.putExtra("mode", Constants.WARNING_SCREEN_MODE_APP_BLOCKER)
        dialogIntent.putExtra("result_id", packageName)
        startActivity(dialogIntent)

    }

    private fun handleFocusModeBlockerResult(result: FocusModeBlocker.FocusModeResult) {
        if (result.isRequestingToUpdateSPData) {
            savedPreferencesLoader.saveFocusModeData(focusModeBlocker.focusModeData)
        }

        if (!result.isBlocked) return

        pressHome()
        Toast.makeText(this, "This app is currently under focus mode", Toast.LENGTH_LONG).show()
    }

    override fun onInterrupt() {
    }

    @SuppressLint("UnspecifiedRegisterReceiverFlag")
    override fun onServiceConnected() {
        super.onServiceConnected()
        setupAppBlocker()
        setupFocusMode()

        val filter = IntentFilter().apply {
            addAction(INTENT_ACTION_REFRESH_FOCUS_MODE)
            addAction(INTENT_ACTION_REFRESH_APP_BLOCKER)
            addAction(INTENT_ACTION_REFRESH_APP_BLOCKER_COOLDOWN)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(refreshReceiver, filter, RECEIVER_EXPORTED)
        } else {
            registerReceiver(refreshReceiver, filter)
        }
    }


    private val refreshReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent == null) return
            when (intent.action) {
                INTENT_ACTION_REFRESH_FOCUS_MODE -> setupFocusMode()
                INTENT_ACTION_REFRESH_APP_BLOCKER -> setupAppBlocker()
                INTENT_ACTION_REFRESH_APP_BLOCKER_COOLDOWN -> {
                    val interval =
                        intent.getIntExtra("selected_time", appBlockerWarning.timeInterval)
                    val coolPackage = intent.getStringExtra("result_id") ?: ""
                    val cooldownUntil =
                        SystemClock.uptimeMillis() + interval
                    appBlocker.putCooldownTo(
                        coolPackage,
                        cooldownUntil
                    )
                    setUpForcedRefreshChecker(coolPackage, cooldownUntil)

                }
            }

        }
    }

    /**
     * Setup a runnable that executes after n millis to check if a package is still being used that was allowed to be used previously
     * as it was put into cooldown or found in cheat-minutes. Basically shows the warning dialog after cooldown is over.
     * @param coolPackage
     * @param endMillis
     */
    private fun setUpForcedRefreshChecker(coolPackage: String, endMillis: Long) {
        if (updateRunnable != null) {
            updateRunnable?.let { handler.removeCallbacks(it) }
            updateRunnable = null
        }
        updateRunnable = Runnable {

            Log.d("AppBlockerService", "Triggered Recheck for  $coolPackage")
            try {
                if (rootInActiveWindow.packageName == coolPackage) {
                    handleAppBlockerResult(
                        AppBlocker.AppBlockerResult(true),
                        coolPackage
                    )
                    lastPackage = ""
                    appBlocker.removeCooldownFrom(coolPackage)
                }
            } catch (e: Exception) {
                Log.e("AppBlockerService", e.toString())
                setUpForcedRefreshChecker(coolPackage, endMillis + 60_000) // recheck after a minute
            }
        }

        handler.postAtTime(updateRunnable!!, endMillis)
    }
    private fun setupAppBlocker() {
        appBlocker.blockedAppsList = savedPreferencesLoader.loadBlockedApps().toHashSet()
        appBlocker.whitelistAppsList = savedPreferencesLoader.loadAppBlockerWhitelist().toHashSet()
        appBlocker.blacklistAppsList = savedPreferencesLoader.loadAppBlockerBlacklist().toHashSet()
        appBlocker.refreshCheatHoursData(savedPreferencesLoader.loadAppBlockerCheatHoursList())

        appBlockerWarning = savedPreferencesLoader.loadAppBlockerWarningInfo()

        pointsOfInterest = savedPreferencesLoader.loadPointsOfInterest()
        geoPolicies = savedPreferencesLoader.loadGeoBlockPolicies()
    }

    private fun collectUsageSnapshot(packageName: String): nethical.digipaws.ai.UsageSnapshot {
        try {
            val usageHelper = nethical.digipaws.utils.UsageStatsHelper(this)
            val now = System.currentTimeMillis()
            val lastHour = usageHelper.getForegroundStatsByTimestamps(now - 60 * 60 * 1000L, now)
                .firstOrNull { it.packageName == packageName }?.totalTime ?: 0L
            val todayList = usageHelper.getForegroundStatsByRelativeDay(0)
            val todayTime = todayList.firstOrNull { it.packageName == packageName }?.totalTime ?: 0L
            val sessions = todayList.firstOrNull { it.packageName == packageName }?.startTimes?.size ?: 0
            return nethical.digipaws.ai.UsageSnapshot(lastHourMs = lastHour, todayMs = todayTime, sessionsToday = sessions)
        } catch (_: Exception) {
            return nethical.digipaws.ai.UsageSnapshot()
        }
    }

    fun setupFocusMode() {
        focusModeBlocker.refreshCheatHoursData(savedPreferencesLoader.loadAutoFocusHoursList())

        val selectedFocusModeApps = savedPreferencesLoader.getFocusModeSelectedApps().toHashSet()
        val focusModeData = savedPreferencesLoader.getFocusModeData()
        focusModeData.whitelist = savedPreferencesLoader.getFocusModeWhitelistApps().toHashSet()
        focusModeData.blacklist = savedPreferencesLoader.getFocusModeBlacklistApps().toHashSet()

        // As all apps wil get blocked except the selected ones, add essential packages that need not be blocked
        // to the list of selected apps
        if (focusModeData.modeType == Constants.FOCUS_MODE_BLOCK_ALL_EX_SELECTED) {
            selectedFocusModeApps.add("com.android.systemui")
            getDefaultLauncherPackageName(packageManager)?.let { selectedFocusModeApps.add(it) }
            getCurrentKeyboardPackageName(this)?.let { selectedFocusModeApps.add(it) }
        }

        focusModeData.selectedApps = selectedFocusModeApps
        focusModeBlocker.focusModeData = focusModeData

    }

    private fun isBlockedByGeoPolicy(packageName: String): Boolean {
        val lat = lastKnownLat ?: return false
        val lon = lastKnownLon ?: return false
        val minuteOfDay = java.util.Calendar.getInstance().let {
            it.get(java.util.Calendar.HOUR_OF_DAY) * 60 + it.get(java.util.Calendar.MINUTE)
        }
        val poiById = pointsOfInterest.associateBy { it.id }
        geoPolicies.forEach { policy ->
            val poi = poiById[policy.poiId] ?: return@forEach
            if (!policy.apps.contains(packageName)) return@forEach
            val inTime = if (policy.startMinutes <= policy.endMinutes) {
                minuteOfDay in policy.startMinutes..policy.endMinutes
            } else {
                minuteOfDay >= policy.startMinutes || minuteOfDay <= policy.endMinutes
            }
            if (inTime && GeoTools.isInsidePoi(lat, lon, poi)) return true
        }
        return false
    }

    override fun onDestroy() {
        super.onDestroy()
        unregisterReceiver(refreshReceiver)
    }

}