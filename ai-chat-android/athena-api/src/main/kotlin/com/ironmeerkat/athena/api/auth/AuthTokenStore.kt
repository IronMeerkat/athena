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
import kotlinx.coroutines.flow.map

/** Stores JWT access/refresh tokens locally using DataStore. */
@Singleton
class AuthTokenStore @Inject constructor(
  private val application: Application,
) {

  private val Application.dataStore: DataStore<Preferences> by preferencesDataStore(name = "auth")

  private val keyAccess = stringPreferencesKey("access_token")
  private val keyRefresh = stringPreferencesKey("refresh_token")

  val accessTokenFlow: Flow<String> = application.dataStore.data.map { it[keyAccess].orEmpty() }
  val refreshTokenFlow: Flow<String> = application.dataStore.data.map { it[keyRefresh].orEmpty() }
  val isLoggedInFlow: Flow<Boolean> = accessTokenFlow.map { it.isNotBlank() }

  suspend fun saveTokens(access: String, refresh: String) {
    application.dataStore.edit { prefs ->
      prefs[keyAccess] = access
      prefs[keyRefresh] = refresh
    }
  }

  suspend fun saveAccessToken(access: String) {
    application.dataStore.edit { prefs ->
      prefs[keyAccess] = access
    }
  }

  suspend fun clear() {
    application.dataStore.edit { prefs ->
      prefs.remove(keyAccess)
      prefs.remove(keyRefresh)
    }
  }
}
