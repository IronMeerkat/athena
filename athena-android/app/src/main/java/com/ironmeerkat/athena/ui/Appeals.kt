package com.ironmeerkat.athena.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun AppealsScreen(onDone: () -> Unit) {
  val input = remember { mutableStateOf("") }
  val timeLeft = remember { mutableStateOf(60) }
  Column(
    modifier = Modifier.fillMaxSize(),
    verticalArrangement = Arrangement.Center,
    horizontalAlignment = Alignment.CenterHorizontally
  ) {
    Text("Appeals (placeholder)")
    Text("Time left: ${timeLeft.value}s")
    Spacer(Modifier.height(12.dp))
    OutlinedTextField(value = input.value, onValueChange = { input.value = it }, label = { Text("Say why you need access") })
    Spacer(Modifier.height(12.dp))
    Button(onClick = onDone) { Text("Send & close") }
  }
}


