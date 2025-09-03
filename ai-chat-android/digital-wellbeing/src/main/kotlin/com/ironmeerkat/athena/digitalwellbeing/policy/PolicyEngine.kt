package com.ironmeerkat.athena.digitalwellbeing.policy

import com.ironmeerkat.athena.digitalwellbeing.db.DecisionDao
import com.ironmeerkat.athena.digitalwellbeing.db.DecisionEntity
import com.ironmeerkat.athena.digitalwellbeing.db.RuleDao
import com.ironmeerkat.athena.digitalwellbeing.db.StateDao
import com.ironmeerkat.athena.digitalwellbeing.db.StateEntity
import com.ironmeerkat.athena.api.AthenaService
import com.ironmeerkat.athena.api.dto.DeviceAttemptRequest
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.withContext
import com.ironmeerkat.athena.core.network.Dispatcher
import com.ironmeerkat.athena.core.network.AIChatDispatchers
import timber.log.Timber

sealed class PolicyDecision(val allow: Boolean) {
  data class Allow(val reason: String) : PolicyDecision(true)
  data class Block(val reason: String) : PolicyDecision(false)
}

data class Target(
  val appPackage: String?,
  val url: String?,
) {
  override fun toString(): String = url ?: appPackage ?: "unknown"
}

@Singleton
class PolicyEngine @Inject constructor(
  private val ruleDao: RuleDao,
  private val decisionDao: DecisionDao,
  private val stateDao: StateDao,
  private val athenaService: AthenaService,
  private val decisionCache: DecisionCache,
  @Dispatcher(AIChatDispatchers.IO) private val ioDispatcher: CoroutineDispatcher,
) {
  private val statePauseKey = "pause_mode" // values: off|soft|hard

  suspend fun onTargetChanged(target: Target): PolicyDecision = withContext(ioDispatcher) {
    Timber.d("onTargetChanged: %s", target)
    val now = System.currentTimeMillis()

    decisionDao.purgeExpired(now)
    ruleDao.purgeExpired(now)

    val cached = decisionCache.get(target.toString(), now)
    if (cached != null) return@withContext cached

    val pause = stateDao.get(statePauseKey)?.value ?: "off"
    Timber.v("pauseMode=%s", pause)
    if (pause == "soft") {
      val decision = PolicyDecision.Allow("Paused (soft)")
      decisionCache.put(target.toString(), decision)
      return@withContext decision
    }

    val rules = ruleDao.getAll()
    val match = rules.firstOrNull { rule ->
      val pattern = rule.pattern
      val t = target.toString()
      when (rule.type) {
        "whitelist", "blacklist" -> t.contains(pattern, ignoreCase = true)
        else -> false
      }
    }
    if (match != null) {
      val decision = when (match.type) {
        "whitelist" -> PolicyDecision.Allow("Local whitelist: ${match.pattern}")
        "blacklist" -> PolicyDecision.Block("Local blacklist: ${match.pattern}")
        else -> PolicyDecision.Allow("Unknown rule type; default allow")
      }
      decisionCache.put(target.toString(), decision)
      return@withContext decision
    }

    // Remote guardian check via DRF
    try {
      val req = DeviceAttemptRequest(
        deviceId = getDeviceId(),
        app = target.appPackage,
        url = target.url,
        ts = null,
      )
      val resp = athenaService.deviceAttempt(req)
      val remoteDecision = when (resp.decision.lowercase()) {
        "allow" -> PolicyDecision.Allow("Guardian allow")
        "block" -> PolicyDecision.Block("Guardian block")
        else -> PolicyDecision.Allow("Guardian unknown -> allow")
      }
      val ttlMs = 60_000L
      decisionDao.upsert(
        DecisionEntity(
          target = target.toString(),
          decision = if (remoteDecision.allow) "allow" else "block",
          reason = "remote",
          decidedAtEpochMillis = now,
          expiresAtEpochMillis = now + ttlMs,
        )
      )
      decisionCache.put(target.toString(), remoteDecision, ttlMs)
      Timber.i("remote decision: allow=%s target=%s", remoteDecision.allow, target)
      remoteDecision
    } catch (t: Throwable) {
      Timber.e(t, "remote check failed for %s", target)
      // Fail-open when remote unavailable unless hard pause
      if (pause == "hard") PolicyDecision.Allow("Paused (hard override)") else PolicyDecision.Allow("Remote failed; allow")
    }
  }

  suspend fun setPause(mode: String) = withContext(ioDispatcher) {
    require(mode in setOf("off", "soft", "hard"))
    stateDao.upsert(StateEntity(statePauseKey, mode))
    Timber.i("setPause: %s", mode)
  }

  suspend fun insertTemporaryWhitelist(targetPattern: String, ttlMinutes: Int) = withContext(ioDispatcher) {
    val expires = System.currentTimeMillis() + ttlMinutes * 60_000L
    ruleDao.upsert(
      com.ironmeerkat.athena.digitalwellbeing.db.RuleEntity(
        pattern = targetPattern,
        type = "whitelist",
        isTemporary = true,
        expiresAtEpochMillis = expires,
      )
    )
    Timber.i("insertTemporaryWhitelist: %s for %d min", targetPattern, ttlMinutes)
  }

  private fun getDeviceId(): String =
    android.os.Build.SERIAL ?: android.os.Build.getSerial()
}


