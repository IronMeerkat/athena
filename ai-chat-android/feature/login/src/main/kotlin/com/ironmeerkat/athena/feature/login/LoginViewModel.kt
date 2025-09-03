package com.ironmeerkat.athena.feature.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ironmeerkat.athena.api.AthenaService
import com.ironmeerkat.athena.api.auth.AuthTokenStore
import com.ironmeerkat.athena.api.dto.TokenObtainPairRequest
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

@HiltViewModel
class LoginViewModel @Inject constructor(
  private val service: AthenaService,
  private val tokenStore: AuthTokenStore,
) : ViewModel() {

  private val _loading = MutableStateFlow(false)
  val loading: StateFlow<Boolean> = _loading

  private val _error = MutableStateFlow<String?>(null)
  val error: StateFlow<String?> = _error

  fun login(username: String, password: String, onSuccess: () -> Unit) {
    _error.value = null
    _loading.value = true
    viewModelScope.launch {
      try {
        val resp = service.tokenObtainPair(TokenObtainPairRequest(username, password))
        tokenStore.saveTokens(resp.access, resp.refresh)
        onSuccess()
      } catch (t: Throwable) {
        _error.value = t.message ?: "Login failed"
      } finally {
        _loading.value = false
      }
    }
  }
}


