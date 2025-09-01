/*
 * Designed and developed by 2024 skydoves (Jaewoong Eum)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.ironmeerkat.athena.feature.messages

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.CornerSize
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.skydoves.landscapist.glide.GlideImage
import dev.jeziellago.compose.markdowntext.MarkdownText
import com.ironmeerkat.athena.core.designsystem.theme.AIChatPreview
import com.ironmeerkat.athena.core.designsystem.theme.AIChatTheme
import com.ironmeerkat.athena.core.model.Channel
import com.ironmeerkat.athena.core.model.Message
import com.ironmeerkat.athena.core.model.mock.MockUtils
import java.util.UUID

@Composable
fun Messages(
  index: Int,
  channel: Channel,
  onBackClick: () -> Unit,
) {
  val messagesViewModel = hiltViewModel<MessagesViewModel, MessagesViewModel.Factory> { factory ->
    factory.create(index)
  }
  val state = rememberLazyListState()
  val messages by messagesViewModel.messages.collectAsStateWithLifecycle()
  val channelState by messagesViewModel.channelState.collectAsStateWithLifecycle()
  val latestResponse by messagesViewModel.latestResponse.collectAsStateWithLifecycle()
  var generatedMessage by remember { mutableStateOf("") }
  val (text, onTextChanged) = remember { mutableStateOf("") }

  LaunchedEffect(key1 = latestResponse) {
    latestResponse?.let {
      // Treat each websocket emission as a complete assistant message.
      generatedMessage += it
      if (generatedMessage.isNotBlank()) {
        messagesViewModel.handleEvents(
          ChatEvent.CompleteGeneration(
            message = generatedMessage,
            sender = "AI",
          ),
        )
        generatedMessage = ""
      }
    }
  }

  // For websocket-based journaling, we complete per emission above.

  LaunchedEffect(key1 = messages, key2 = generatedMessage) {
    if (messages.isNotEmpty()) {
      state.scrollToItem(messages.lastIndex)
    }
  }

  Column(modifier = Modifier.fillMaxSize()) {
    MessagesAppBar(channel = channel, onBackClick = onBackClick)

    if (channelState != null) {
      MessageList(messages = messages, state = state, generatedMessage = generatedMessage)
    } else {
      Box(modifier = Modifier.fillMaxSize()) {
        CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
      }
    }

    MessageInput(
      text = text,
      onTextChanged = onTextChanged,
      onSendMessage = {
        messagesViewModel.handleEvents(
          ChatEvent.SendMessage(
            message = text,
            sender = "User",
          ),
        )
      },
    )
  }
}

@Composable
private fun MessagesAppBar(
  channel: Channel,
  onBackClick: () -> Unit,
) {
  Box(
    modifier = Modifier
      .background(AIChatTheme.colors.background)
      .fillMaxWidth()
      .padding(8.dp),
  ) {
    Icon(
      modifier = Modifier
        .align(Alignment.CenterStart)
        .clip(CircleShape)
        .size(30.dp)
        .clickable { onBackClick.invoke() },
      tint = Color.White,
      imageVector = Icons.AutoMirrored.Default.ArrowBack,
      contentDescription = null,
    )

    Text(
      modifier = Modifier.align(Alignment.Center),
      text = "Channel${channel.id.take(3)}",
      fontWeight = FontWeight.Bold,
      color = AIChatTheme.colors.textHighEmphasis,
      fontSize = 17.sp,
    )
  }
}

@Composable
private fun ColumnScope.MessageList(
  messages: List<Message>,
  state: LazyListState,
  generatedMessage: String,
) {
  LazyColumn(
    state = state,
    modifier = Modifier
      .fillMaxSize()
      .weight(1f)
      .padding(vertical = 16.dp, horizontal = 12.dp),
  ) {
    items(items = messages, key = { it.id }) { message ->
      if (message.isBot) {
        BotMessageItem(message = message)
      } else {
        UserMessageItem(message = message)
      }
    }

    if (generatedMessage.isNotBlank()) {
      item {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
          BotMessageItem(
            message = Message(
              id = UUID.randomUUID().toString(),
              message = generatedMessage,
              sender = "AI",
            ),
          )

          CircularProgressIndicator(modifier = Modifier.size(34.dp))
        }
      }
    }
  }
}

@Composable
private fun BotMessageItem(message: Message) {
  Box(
    modifier = Modifier
      .fillMaxWidth()
      .padding(bottom = 12.dp),
    contentAlignment = Alignment.CenterStart,
  ) {
    Row {
      Image(
        modifier = Modifier
          .clip(CircleShape)
          .size(42.dp),
        painter = painterResource(com.ironmeerkat.athena.core.designsystem.R.drawable.ic_gemini),
        contentDescription = null,
      )

      Spacer(modifier = Modifier.width(8.dp))

      MarkdownText(
        modifier = Modifier
          .fillMaxWidth()
          .background(
            color = AIChatTheme.colors.primary,
            shape = RoundedCornerShape(12.dp).copy(bottomStart = CornerSize(0.dp)),
          )
          .padding(12.dp),
        markdown = message.message,
        style = TextStyle(color = Color.White),
      )
    }
  }
}

@Composable
private fun UserMessageItem(message: Message) {
  Box(
    modifier = Modifier
      .fillMaxWidth()
      .padding(bottom = 12.dp),
    contentAlignment = Alignment.CenterEnd,
  ) {
    Text(
      modifier = Modifier
        .background(
          color = AIChatTheme.colors.tertiary,
          shape = RoundedCornerShape(12.dp).copy(bottomEnd = CornerSize(0.dp)),
        )
        .padding(12.dp),
      text = message.message,
      color = Color.White,
    )
  }
}

@Composable
private fun MessageInput(
  text: String,
  onTextChanged: (String) -> Unit,
  onSendMessage: (String) -> Unit,
) {
  val canSend = text.isNotBlank()

  Row(
    modifier = Modifier
      .fillMaxWidth()
      .padding(vertical = 8.dp, horizontal = 16.dp),
  ) {
    GlideImage(
      imageModel = { "https://placecats.com/300/200" },
      modifier = Modifier
        .padding(end = 8.dp)
        .size(48.dp)
        .clip(CircleShape)
        .align(Alignment.CenterVertically),
    )

    TextField(
      modifier = Modifier.fillMaxWidth(),
      value = text,
      onValueChange = onTextChanged,
      textStyle = TextStyle(fontSize = 14.sp),
      trailingIcon = {
        Icon(
          modifier = Modifier
            .padding(end = 8.dp)
            .clickable {
              if (canSend) {
                onSendMessage.invoke(text)
                onTextChanged.invoke("")
              }
            },
          imageVector = Icons.AutoMirrored.Default.Send,
          tint = if (canSend) {
            AIChatTheme.colors.primary
          } else {
            AIChatTheme.colors.black20
          },
          contentDescription = null,
        )
      },
      shape = RoundedCornerShape(12.dp),
      maxLines = 3,
      colors = TextFieldDefaults.colors(
        focusedTextColor = AIChatTheme.colors.textHighEmphasis,
        unfocusedTextColor = AIChatTheme.colors.textHighEmphasis,
        focusedContainerColor = AIChatTheme.colors.black80,
        unfocusedContainerColor = AIChatTheme.colors.black80,
        disabledContainerColor = AIChatTheme.colors.black80,
        focusedIndicatorColor = Color.Transparent,
        unfocusedIndicatorColor = Color.Transparent,
        disabledIndicatorColor = Color.Transparent,
      ),
      keyboardOptions = KeyboardOptions(
        imeAction = ImeAction.Send,
      ),
      keyboardActions = KeyboardActions(
        onSend = {
          if (canSend) {
            onSendMessage.invoke(text)
            onTextChanged.invoke("")
          }
        },
      ),
      placeholder = {
        Text(
          text = "Ask me anything!",
          color = AIChatTheme.colors.textPlaceholder,
          fontSize = 14.sp,
        )
      },
    )
  }
}

@AIChatPreview
@Composable
private fun MessageListPreview() {
  AIChatTheme {
    Column(modifier = Modifier.background(AIChatTheme.colors.background)) {
      MessagesAppBar(channel = MockUtils.channel, onBackClick = {})

      MessageList(
        messages = listOf(
          Message(
            sender = "AI",
            message = "How can I help you?",
          ),
          Message(
            sender = "User",
            message = "What is Android?",
          ),
          Message(
            sender = "AI",
            message = "Android is Android",
          ),
        ),
        state = rememberLazyListState(),
        generatedMessage = "",
      )
    }
  }
}
