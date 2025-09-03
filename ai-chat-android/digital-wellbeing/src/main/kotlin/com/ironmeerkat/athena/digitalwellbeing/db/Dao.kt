package com.ironmeerkat.athena.digitalwellbeing.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Upsert

@Dao
interface RuleDao {
  @Query("SELECT * FROM rules")
  suspend fun getAll(): List<RuleEntity>

  @Insert(onConflict = OnConflictStrategy.REPLACE)
  suspend fun insertAll(rules: List<RuleEntity>)

  @Upsert
  suspend fun upsert(rule: RuleEntity)

  @Query("DELETE FROM rules WHERE id = :id")
  suspend fun deleteById(id: Long)

  @Query("DELETE FROM rules WHERE isTemporary = 1 AND (expiresAtEpochMillis IS NOT NULL AND expiresAtEpochMillis < :now)")
  suspend fun purgeExpired(now: Long)
}

@Dao
interface DecisionDao {
  @Query("SELECT * FROM decisions WHERE target = :target ORDER BY decidedAtEpochMillis DESC LIMIT 1")
  suspend fun getLatestForTarget(target: String): DecisionEntity?

  @Upsert
  suspend fun upsert(decision: DecisionEntity)

  @Query("DELETE FROM decisions WHERE expiresAtEpochMillis IS NOT NULL AND expiresAtEpochMillis < :now")
  suspend fun purgeExpired(now: Long)
}

@Dao
interface StateDao {
  @Upsert
  suspend fun upsert(state: StateEntity)

  @Query("SELECT * FROM state WHERE key = :key LIMIT 1")
  suspend fun get(key: String): StateEntity?
}


