package com.ironmeerkat.athena

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import android.app.Activity
import com.ironmeerkat.athena.ui.AppealsScreen
import com.ironmeerkat.athena.ui.BlockScreen
import com.ironmeerkat.athena.ui.ChatScreen
import com.ironmeerkat.athena.ui.HomeScreen
import com.ironmeerkat.athena.ui.NudgeSheet
import com.ironmeerkat.athena.ui.PermissionsHub
import com.ironmeerkat.athena.ui.GoalsScreen
import com.ironmeerkat.athena.ui.JournalScreen
import com.ironmeerkat.athena.ui.SettingsScreen
import com.ironmeerkat.athena.ui.NotificationsFeed
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import nethical.digipaws.bridge.BlockerEvent
import nethical.digipaws.bridge.BlockerEvents
import com.ironmeerkat.athena.nav.NavRoutes

class MainActivity : ComponentActivity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    setContent { AthenaApp() }
  }
}

@Composable
fun AthenaApp() {
  Surface(color = MaterialTheme.colorScheme.background) {
    val nav = rememberNavController()
    val ctx = LocalContext.current
    LaunchedEffect(Unit) {
      BlockerEvents.events.onEach {
        when (it) {
          is BlockerEvent.Block -> nav.navigate(NavRoutes.BLOCK)
          is BlockerEvent.Nudge -> nav.navigate(NavRoutes.NUDGE)
        }
      }.launchIn(this)
      // Handle deep link destination from notification
      val activityIntent = (ctx as? Activity)?.intent
      val destExtra = activityIntent?.getStringExtra("dest")
      val dest = destExtra ?: activityIntent?.data?.getQueryParameter("dest")
      when (dest) {
        NavRoutes.NUDGE -> nav.navigate(NavRoutes.NUDGE)
        NavRoutes.BLOCK -> nav.navigate(NavRoutes.BLOCK)
        NavRoutes.CHAT -> nav.navigate(NavRoutes.CHAT)
      }
    }
    NavHost(navController = nav, startDestination = NavRoutes.HOME) {
      composable(NavRoutes.HOME) {
        HomeScreen(
          onOpenChat = { nav.navigate(NavRoutes.CHAT) },
          onOpenPermissions = { nav.navigate(NavRoutes.PERMISSIONS) },
          onOpenGoals = { nav.navigate(NavRoutes.GOALS) },
          onOpenJournal = { nav.navigate(NavRoutes.JOURNAL) },
          onOpenSettings = { nav.navigate(NavRoutes.SETTINGS) },
          onOpenFeed = { nav.navigate(NavRoutes.FEED) },
          onAppeal = { nav.navigate(NavRoutes.APPEALS) },
          onPause = { /* TODO: send pause request */ }
        )
      }
      composable(NavRoutes.CHAT) { ChatScreen(onBack = { nav.popBackStack() }) }
      composable(NavRoutes.BLOCK) { BlockScreen(reason = "Blocked", onAppeal = { nav.navigate(NavRoutes.APPEALS) }, onBackToWork = { nav.popBackStack(NavRoutes.HOME, inclusive = false) }) }
      composable(NavRoutes.NUDGE) { NudgeSheet(eventId = "", ttl = 2, onAccept = { nav.popBackStack() }, onDecline = { nav.popBackStack() }) }
      composable(NavRoutes.APPEALS) { AppealsScreen(onDone = { nav.popBackStack(NavRoutes.HOME, inclusive = false) }) }
      composable(NavRoutes.PERMISSIONS) { PermissionsHub(onBack = { nav.popBackStack() }) }
      composable(NavRoutes.GOALS) { GoalsScreen(onBack = { nav.popBackStack() }) }
      composable(NavRoutes.JOURNAL) { JournalScreen(onBack = { nav.popBackStack() }) }
      composable(NavRoutes.SETTINGS) { SettingsScreen(onBack = { nav.popBackStack() }) }
      composable(NavRoutes.FEED) { NotificationsFeed(onBack = { nav.popBackStack() }) }
    }
  }
}


