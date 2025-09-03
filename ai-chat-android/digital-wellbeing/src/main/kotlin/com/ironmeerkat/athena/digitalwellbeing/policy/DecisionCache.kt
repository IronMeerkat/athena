package com.ironmeerkat.athena.digitalwellbeing.policy

import java.util.concurrent.ConcurrentHashMap
import timber.log.Timber

data class CachedDecision(
  val decision: PolicyDecision,
  val expiresAtEpochMillis: Long,
)

class DecisionCache(
  private val defaultTtlMillis: Long = 30_000,
) {
  private val map = ConcurrentHashMap<String, CachedDecision>()

  fun get(target: String, now: Long = System.currentTimeMillis()): PolicyDecision? {
    val cached = map[target] ?: return null
    return if (cached.expiresAtEpochMillis > now) cached.decision else {
      map.remove(target)
      Timber.v("cache expired: %s", target)
      null
    }
  }

  fun put(target: String, decision: PolicyDecision, ttlMillis: Long = defaultTtlMillis, now: Long = System.currentTimeMillis()) {
    map[target] = CachedDecision(decision, now + ttlMillis)
    Timber.v("cache put: %s ttl=%d", target, ttlMillis)
  }

  fun clear() = map.clear()
}


