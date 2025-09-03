package com.ironmeerkat.athena

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ironmeerkat.athena.api.auth.AuthTokenStore
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn

@HiltViewModel
class AuthGateViewModel @Inject constructor(
  tokenStore: AuthTokenStore,
) : ViewModel() {
  val isLoggedIn: StateFlow<Boolean> = tokenStore.isLoggedInFlow
    .stateIn(viewModelScope, SharingStarted.Eagerly, false)
}


