package com.ironmeerkat.athena.digitalwellbeing.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
  entities = [RuleEntity::class, DecisionEntity::class, StateEntity::class],
  version = 1,
  exportSchema = false,
)
abstract class DigitalWellbeingDatabase : RoomDatabase() {
  abstract fun ruleDao(): RuleDao
  abstract fun decisionDao(): DecisionDao
  abstract fun stateDao(): StateDao
}


