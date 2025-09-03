package com.ironmeerkat.athena.digitalwellbeing.db

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "rules")
data class RuleEntity(
  @PrimaryKey(autoGenerate = true) val id: Long = 0,
  val pattern: String,
  val type: String, // "whitelist" or "blacklist"
  val isTemporary: Boolean = false,
  val expiresAtEpochMillis: Long? = null,
)

@Entity(tableName = "decisions")
data class DecisionEntity(
  @PrimaryKey(autoGenerate = true) val id: Long = 0,
  val target: String, // app package or URL
  val decision: String, // "allow" or "block"
  val reason: String,
  val decidedAtEpochMillis: Long,
  val expiresAtEpochMillis: Long?,
)

@Entity(tableName = "state")
data class StateEntity(
  @PrimaryKey val key: String,
  val value: String,
)


