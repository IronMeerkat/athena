package com.ironmeerkat.athena.digitalwellbeing.di

import android.content.Context
import androidx.room.Room
import com.ironmeerkat.athena.digitalwellbeing.db.DecisionDao
import com.ironmeerkat.athena.digitalwellbeing.db.DigitalWellbeingDatabase
import com.ironmeerkat.athena.digitalwellbeing.db.RuleDao
import com.ironmeerkat.athena.digitalwellbeing.db.StateDao
import com.ironmeerkat.athena.digitalwellbeing.policy.DecisionCache
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
internal object WellbeingModule {

  @Provides
  @Singleton
  fun provideDatabase(@ApplicationContext context: Context): DigitalWellbeingDatabase =
    Room.databaseBuilder(context, DigitalWellbeingDatabase::class.java, "digital_wellbeing.db")
      .fallbackToDestructiveMigration()
      .build()

  @Provides
  fun provideRuleDao(db: DigitalWellbeingDatabase): RuleDao = db.ruleDao()

  @Provides
  fun provideDecisionDao(db: DigitalWellbeingDatabase): DecisionDao = db.decisionDao()

  @Provides
  fun provideStateDao(db: DigitalWellbeingDatabase): StateDao = db.stateDao()

  @Provides
  @Singleton
  fun provideDecisionCache(): DecisionCache = DecisionCache()
}


