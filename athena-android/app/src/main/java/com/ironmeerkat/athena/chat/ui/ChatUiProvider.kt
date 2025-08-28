package com.ironmeerkat.athena.chat.ui

import androidx.compose.runtime.Composable

interface ChatUiProvider {
  @Composable
  fun ChatScreen(
    onBack: () -> Unit
  )
}


