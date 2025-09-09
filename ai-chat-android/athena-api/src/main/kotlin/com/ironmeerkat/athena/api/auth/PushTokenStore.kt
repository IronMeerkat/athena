package com.ironmeerkat.athena.api.auth

import android.app.Application
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

/** Stores the latest FCM registration token for targeted push. */
@Singleton
class PushTokenStore @Inject constructor(
  private val application: Application,
) {

  private val Application.dataStore: DataStore<Preferences> by preferencesDataStore(name = "push")

  private val keyToken = stringPreferencesKey("fcm_token")

  val tokenFlow: Flow<String> = application.dataStore.data.map { it[keyToken].orEmpty() }

  suspend fun saveToken(token: String) {
    application.dataStore.edit { prefs ->
      prefs[keyToken] = token
    }
  }

  suspend fun getToken(): String = tokenFlow.first()

  suspend fun clear() {
    application.dataStore.edit { prefs ->
      prefs.remove(keyToken)
    }
  }
}


