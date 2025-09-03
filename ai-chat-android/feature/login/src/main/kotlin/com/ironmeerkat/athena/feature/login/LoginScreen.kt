package com.ironmeerkat.athena.feature.login

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

@Composable
fun Login(onLoggedIn: () -> Unit, modifier: Modifier = Modifier, viewModel: LoginViewModel = hiltViewModel()) {
  var username by remember { mutableStateOf("") }
  var password by remember { mutableStateOf("") }

  Column(
    modifier = modifier.fillMaxSize().padding(24.dp),
    verticalArrangement = Arrangement.Center,
    horizontalAlignment = Alignment.CenterHorizontally,
  ) {
    OutlinedTextField(value = username, onValueChange = { username = it }, label = { Text("Username") })
    OutlinedTextField(value = password, onValueChange = { password = it }, label = { Text("Password") })
    Button(onClick = { viewModel.login(username, password, onLoggedIn) }, contentPadding = PaddingValues(horizontal = 24.dp, vertical = 12.dp)) {
      Text("Login")
    }
    viewModel.error.value?.let { Text(it) }
  }
}


