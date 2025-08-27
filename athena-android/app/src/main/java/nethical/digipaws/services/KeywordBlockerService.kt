package nethical.digipaws.services

import android.annotation.SuppressLint
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.SystemClock
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.Toast
import nethical.digipaws.blockers.KeywordBlocker
import nethical.digipaws.blockers.ViewBlocker
import nethical.digipaws.data.blockers.KeywordPacks
import nethical.digipaws.ui.activity.AppealActivity
import nethical.digipaws.net.ServerClient
import java.net.URI

class KeywordBlockerService : BaseBlockingService() {

    private var refreshCooldown = 1000
    private var lastEventTimeStamp = 0L
    companion object {
        const val INTENT_ACTION_REFRESH_BLOCKED_KEYWORD_LIST =
            "nethical.digipaws.refresh.keywordblocker.blockedwords"

        const val INTENT_ACTION_REFRESH_CONFIG =
            "nethical.digipaws.refresh.keywordblocker.config"

        const val INTENT_ACTION_TEMP_WHITELIST_KEYWORD =
            "nethical.digipaws.keyword.temp_whitelist"
    }

    private val keywordBlocker = KeywordBlocker(this)
    private val serverClient by lazy { ServerClient(this) }

    private var KbIgnoredApps: HashSet<String> = hashSetOf()

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {

        if (!isDelayOver(
                lastEventTimeStamp,
                refreshCooldown
            ) || event == null || event.packageName == "nethical.digipaws" || KbIgnoredApps.contains(
                event.packageName
            )
        ) {
            return
        }
        val rootnode: AccessibilityNodeInfo? = rootInActiveWindow
        Log.d("KeywordBlocker", "Searching Keywords")
        handleKeywordBlockerResult(keywordBlocker.checkIfUserGettingFreaky(rootnode, event))

        // Domain-level classification via server when within schedule
        classifyDomainIfNeeded(rootnode, event)

        lastEventTimeStamp = SystemClock.uptimeMillis()

    }

    override fun onInterrupt() {
    }

    @SuppressLint("UnspecifiedRegisterReceiverFlag")
    override fun onServiceConnected() {
        super.onServiceConnected()
        setupBlockedWords()
        setupConfig()

        val filter = IntentFilter().apply {
            addAction(INTENT_ACTION_REFRESH_BLOCKED_KEYWORD_LIST)
            addAction(INTENT_ACTION_REFRESH_CONFIG)
            addAction(INTENT_ACTION_TEMP_WHITELIST_KEYWORD)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(refreshReceiver, filter, RECEIVER_EXPORTED)
        } else {
            registerReceiver(refreshReceiver, filter)
        }
    }


    private val refreshReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                INTENT_ACTION_REFRESH_BLOCKED_KEYWORD_LIST -> setupBlockedWords()
                INTENT_ACTION_REFRESH_CONFIG -> setupConfig()
                INTENT_ACTION_TEMP_WHITELIST_KEYWORD -> {
                    val keyword = intent.getStringExtra("keyword") ?: return
                    val duration = intent.getIntExtra("selected_time", 0)
                    if (duration > 0) {
                        keywordBlocker.addTempWhitelist(keyword, SystemClock.uptimeMillis() + duration)
                    }
                }
            }
        }
    }

    private fun handleKeywordBlockerResult(result: KeywordBlocker.KeywordBlockerResult) {
        if (result.resultDetectWord == null) return
        Toast.makeText(
            this,
            "Blocked keyword ${result.resultDetectWord} was found.",
            Toast.LENGTH_LONG
        ).show()
        if (result.isHomePressRequested) {
            pressHome()
        }
        // Launch appeals for keywords
        val intent = Intent(this, AppealActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
            putExtra("entity_type", "keyword")
            putExtra("keyword", result.resultDetectWord)
        }
        startActivity(intent)
    }

    private fun classifyDomainIfNeeded(rootnode: AccessibilityNodeInfo?, event: AccessibilityEvent) {
        try {
            if (rootnode == null) return
            val pkg = event.packageName?.toString() ?: return
            val urlBarInfo = KeywordBlocker.URL_BAR_ID_LIST[pkg] ?: return
            val idPrefixPart = "$pkg:id/"
            val displayUrlTextNode = ViewBlocker.findElementById(
                rootnode,
                idPrefixPart + urlBarInfo.displayUrlBarId
            ) ?: return
            val text = displayUrlTextNode.text?.toString() ?: return
            val host = extractHost(text) ?: return

            // Apply lists
            val whitelist = savedPreferencesLoader.loadDomainWhitelist()
            val blacklist = savedPreferencesLoader.loadDomainBlacklist()
            if (whitelist.any { host.contains(it, ignoreCase = true) }) return
            if (blacklist.any { host.contains(it, ignoreCase = true) }) {
                pressHome()
                launchAppealForKeyword(host)
                return
            }

            // Only ask server within active schedule
            if (!nethical.digipaws.utils.ScheduleUtils.isWithinScheduleNow(this)) return
            val urlText = text
            val decision = serverClient.classifyUrl(urlText) ?: return
            if (decision.shouldBlock) {
                pressHome()
                launchAppealForKeyword(host)
            }
        } catch (_: Exception) {
        }
    }

    private fun extractHost(text: String): String? {
        return try {
            var t = text
            if (!t.contains("://")) t = "https://$t"
            val uri = URI(t)
            uri.host
        } catch (_: Exception) {
            null
        }
    }

    private fun launchAppealForKeyword(keyword: String) {
        val intent = Intent(this, AppealActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
            putExtra("entity_type", "keyword")
            putExtra("keyword", keyword)
        }
        startActivity(intent)
    }


    private fun setupBlockedWords() {
        val keywords = savedPreferencesLoader.loadBlockedKeywords().toMutableSet()
        val sp = getSharedPreferences("keyword_blocker_packs", Context.MODE_PRIVATE)
        val isAdultBlockerOn = sp.getBoolean("adult_blocker", false)
        if (isAdultBlockerOn) {
            keywords.addAll(KeywordPacks.adultKeywords)
        }
        keywordBlocker.blockedKeyword = keywords.toHashSet()
    }

    private fun setupConfig() {
        val sp = getSharedPreferences("keyword_blocker_configs", Context.MODE_PRIVATE)

        keywordBlocker.isSearchAllTextFields = sp.getBoolean("search_all_text_fields", false)
        keywordBlocker.redirectUrl =
            sp.getString("redirect_url", "https://www.youtube.com/watch?v=x31tDT-4fQw&t=1s")
                .toString()

        if (keywordBlocker.isSearchAllTextFields) {
            refreshCooldown = 5000
        }

        KbIgnoredApps = savedPreferencesLoader.getKeywordBlockerIgnoredApps().toHashSet()
    }



    override fun onDestroy() {
        super.onDestroy()
        unregisterReceiver(refreshReceiver)
    }
}