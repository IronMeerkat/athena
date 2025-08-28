package com.ironmeerkat.athena.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.ironmeerkat.athena.di.ServiceLocator
import com.ironmeerkat.athena.chat.ui.ChatUiProvider
import com.ironmeerkat.athena.chat.ui.compose.ComposeChatUiProvider
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay

@Composable
fun HomeScreen(
  onOpenChat: () -> Unit,
  onOpenPermissions: () -> Unit,
  onOpenGoals: () -> Unit,
  onOpenJournal: () -> Unit,
  onOpenSettings: () -> Unit,
  onOpenFeed: () -> Unit,
  onAppeal: () -> Unit,
  onPause: () -> Unit
) {
  Column(
    modifier = Modifier.fillMaxSize(),
    verticalArrangement = Arrangement.Center,
    horizontalAlignment = Alignment.CenterHorizontally
  ) {
    Text("Athena Home")
    Spacer(Modifier.height(12.dp))
    Button(onClick = onOpenChat) { Text("Open Chat") }
    Spacer(Modifier.height(8.dp))
    OutlinedButton(onClick = onOpenPermissions) { Text("Permissions Hub") }
    Spacer(Modifier.height(8.dp))
    OutlinedButton(onClick = onOpenGoals) { Text("Goals") }
    Spacer(Modifier.height(8.dp))
    OutlinedButton(onClick = onOpenJournal) { Text("Journal") }
    Spacer(Modifier.height(8.dp))
    OutlinedButton(onClick = onOpenSettings) { Text("Settings") }
    Spacer(Modifier.height(8.dp))
    OutlinedButton(onClick = onOpenFeed) { Text("Notifications Feed") }
    Spacer(Modifier.height(8.dp))
    Button(onClick = onAppeal) { Text("Appeal") }
    Spacer(Modifier.height(8.dp))
    Button(onClick = onPause) { Text("Pause 5m") }
  }
}

@Composable
fun ChatScreen(onBack: () -> Unit) {
  // Obtain the active chat UI provider; using Compose provider by default.
  val provider: ChatUiProvider = ComposeChatUiProvider()
  provider.ChatScreen(onBack = onBack)
}

@Composable
fun GoalsScreen(onBack: () -> Unit) {
  Column(
    modifier = Modifier.fillMaxSize(),
    verticalArrangement = Arrangement.Center,
    horizontalAlignment = Alignment.CenterHorizontally
  ) {
    Text("Goals (placeholder)")
    Spacer(Modifier.height(12.dp))
    OutlinedButton(onClick = onBack) { Text("Back") }
  }
}

@Composable
fun JournalScreen(onBack: () -> Unit) {
  Column(
    modifier = Modifier.fillMaxSize(),
    verticalArrangement = Arrangement.Center,
    horizontalAlignment = Alignment.CenterHorizontally
  ) {
    Text("Journal (placeholder)")
    Spacer(Modifier.height(12.dp))
    OutlinedButton(onClick = onBack) { Text("Back") }
  }
}

@Composable
fun SettingsScreen(onBack: () -> Unit) {
  Column(
    modifier = Modifier.fillMaxSize(),
    verticalArrangement = Arrangement.Center,
    horizontalAlignment = Alignment.CenterHorizontally
  ) {
    Text("Settings (placeholder)")
    Spacer(Modifier.height(12.dp))
    OutlinedButton(onClick = onBack) { Text("Back") }
  }
}

@Composable
fun NotificationsFeed(onBack: () -> Unit) {
  Column(
    modifier = Modifier.fillMaxSize(),
    verticalArrangement = Arrangement.Center,
    horizontalAlignment = Alignment.CenterHorizontally
  ) {
    Text("Notifications Feed (placeholder)")
    Spacer(Modifier.height(12.dp))
    OutlinedButton(onClick = onBack) { Text("Back") }
  }
}

@Composable
fun BlockScreen(reason: String, onAppeal: () -> Unit, onBackToWork: () -> Unit) {
  Column(
    modifier = Modifier.fillMaxSize(),
    verticalArrangement = Arrangement.Center,
    horizontalAlignment = Alignment.CenterHorizontally
  ) {
    Text("Blocked")
    Text(reason)
    Spacer(Modifier.height(12.dp))
    OutlinedButton(onClick = onBackToWork) { Text("Back to work") }
    Spacer(Modifier.height(8.dp))
    Button(onClick = onAppeal) { Text("Appeal") }
  }
}

@Composable
fun NudgeSheet(eventId: String, ttl: Int, onAccept: () -> Unit, onDecline: () -> Unit) {
  Column(
    modifier = Modifier.fillMaxSize(),
    verticalArrangement = Arrangement.Center,
    horizontalAlignment = Alignment.CenterHorizontally
  ) {
    var accepting by remember { mutableStateOf(false) }
    var countdown by remember { mutableStateOf(ttl * 60) }
    Text("Nudge: $ttl min")
    Spacer(Modifier.height(12.dp))
    Button(onClick = {
      if (!accepting) {
        accepting = true
        CoroutineScope(Dispatchers.IO).launch {
          runCatching { ServiceLocator.devicePolicyClient.acceptNudge(eventId, ttl) }
          // start countdown UI; when ends, close
          while (countdown > 0) {
            delay(1000)
            countdown -= 1
          }
          onAccept()
          accepting = false
        }
      }
    }) { Text(if (accepting) "${countdown}s" else "Accept") }
    Spacer(Modifier.height(8.dp))
    OutlinedButton(onClick = onDecline) { Text("Not now") }
  }
}

// AppealsScreen moved to Appeals.kt
// PermissionsHub moved to PermissionsHub.kt


