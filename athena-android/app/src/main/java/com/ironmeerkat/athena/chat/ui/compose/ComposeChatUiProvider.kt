package com.ironmeerkat.athena.chat.ui.compose

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ironmeerkat.athena.chat.ui.ChatUiProvider
import com.ironmeerkat.athena.chat.vm.ChatViewModel
import com.ironmeerkat.athena.chat.model.Sender
import com.ironmeerkat.athena.chat.model.UiMessage
import com.ironmeerkat.athena.chat.vm.ConversationsViewModel

class ComposeChatUiProvider : ChatUiProvider {
  @Composable
  override fun ChatScreen(onBack: () -> Unit) {
    val convVm: ConversationsViewModel = viewModel(factory = ConversationsViewModel.factory)
    val vm: ChatViewModel = viewModel(factory = ChatViewModel.factory)
    ComposeChatScaffold(convVm = convVm, chatVm = vm, onBack = onBack)
  }
}

@Composable
private fun ComposeChatScaffold(convVm: ConversationsViewModel, chatVm: ChatViewModel, onBack: () -> Unit) {
  val conversations by convVm.conversations.collectAsState()
  val activeId by convVm.activeId.collectAsState()
  val messages by chatVm.messages.collectAsState()
  var input by remember { mutableStateOf("") }

  Column(modifier = Modifier.fillMaxSize().padding(12.dp)) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
      OutlinedButton(onClick = onBack) { Text("Back") }
      Text("Athena Chat", style = MaterialTheme.typography.titleMedium)
      Spacer(Modifier.height(0.dp))
    }
    Spacer(Modifier.height(8.dp))
    Row(modifier = Modifier.weight(1f).fillMaxWidth()) {
      // Side panel: conversations list
      Box(modifier = Modifier.width(220.dp).padding(end = 8.dp)) {
        LazyColumn(modifier = Modifier.fillMaxSize()) {
          items(conversations) { convo ->
            val isActive = convo.id == activeId
            Surface(
              color = if (isActive) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant,
              modifier = Modifier.fillMaxWidth().padding(bottom = 6.dp).clip(MaterialTheme.shapes.small)
            ) {
              Row(
                modifier = Modifier.fillMaxWidth().padding(10.dp),
                verticalAlignment = Alignment.CenterVertically
              ) {
                Text(convo.title, modifier = Modifier.weight(1f))
                OutlinedButton(onClick = { convVm.select(convo.id); chatVm.setConversation(convo.id) }) { Text("Open") }
              }
            }
          }
        }
      }
      // Main chat area
      LazyColumn(modifier = Modifier.weight(1f).fillMaxWidth()) {
        items(messages) { msg -> MessageBubble(msg) }
      }
    }
    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
      TextField(
        modifier = Modifier.weight(1f),
        value = input,
        onValueChange = { input = it },
        placeholder = { Text("Message…") }
      )
      Spacer(Modifier.height(0.dp))
      Button(
        onClick = {
          val text = input.trim()
          if (text.isNotEmpty()) {
            chatVm.send(text)
            input = ""
          }
        }
      ) { Text("Send") }
    }
  }
}

@Composable
private fun MessageBubble(msg: UiMessage) {
  val isUser = msg.sender == Sender.USER
  val bg = if (isUser) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant
  val fg = if (isUser) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant
  Row(
    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
    horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
  ) {
    Surface(color = bg, contentColor = fg, modifier = Modifier.clip(MaterialTheme.shapes.medium)) {
      Text(msg.text, modifier = Modifier.padding(10.dp))
    }
  }
}


