package com.ironmeerkat.athena.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun ActivePolicyBanner(name: String, ttlMinutes: Int, onDetails: () -> Unit) {
  Surface(tonalElevation = 2.dp) {
    Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
      Text(text = "Policy: $name ($ttlMinutes m)")
      Spacer(Modifier.width(8.dp))
      OutlinedButton(onClick = onDetails) { Text("Details") }
    }
  }
}

@Composable
fun BlockActions(onAppeal: () -> Unit, onBackToWork: () -> Unit) {
  Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
    OutlinedButton(onClick = onBackToWork) { Text("Back to work") }
    Button(onClick = onAppeal) { Text("Appeal") }
  }
}


