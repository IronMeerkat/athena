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
package com.ironmeerkat.athena.feature.channels

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.skydoves.balloon.compose.Balloon
import com.ironmeerkat.athena.core.designsystem.theme.AIChatPreview
import com.ironmeerkat.athena.core.designsystem.theme.AIChatTheme
import com.ironmeerkat.athena.core.model.Channel
import com.ironmeerkat.athena.core.model.mock.MockUtils

@Composable
fun Channels(
  channelsViewModel: ChannelsViewModel = hiltViewModel(),
  navigateToMessages: (Int, Channel) -> Unit,
) {
  val channels by channelsViewModel.channels.collectAsStateWithLifecycle()

  Box(
    modifier = Modifier
      .fillMaxSize()
      .background(AIChatTheme.colors.background),
  ) {
    Column(modifier = Modifier.fillMaxSize()) {
      ChannelAppBar()

      ChannelContentBody(
        channels = channels,
        onChannelClick = { index, channel -> navigateToMessages.invoke(index, channel) },
      )
    }

    ChannelFloatingButton(
      channelSize = channels.size,
      channelsViewModel = channelsViewModel,
    )
  }
}

@Composable
private fun ChannelAppBar() {
  Box(
    modifier = Modifier
      .background(AIChatTheme.colors.background)
      .fillMaxWidth()
      .padding(8.dp),
  ) {
    Text(
      modifier = Modifier.align(Alignment.Center),
      text = "AI ChatBot",
      fontWeight = FontWeight.Bold,
      color = AIChatTheme.colors.textHighEmphasis,
      fontSize = 17.sp,
    )

    Image(
      modifier = Modifier
        .align(Alignment.CenterEnd)
        .clip(CircleShape)
        .size(42.dp),
      painter = painterResource(com.ironmeerkat.athena.core.designsystem.R.drawable.ic_logo_stream),
      contentDescription = null,
    )
  }
}

@Composable
private fun ChannelContentBody(
  channels: List<Channel>,
  onChannelClick: (Int, Channel) -> Unit,
) {
  LazyColumn(modifier = Modifier.fillMaxSize()) {
    itemsIndexed(items = channels, key = { _, item -> item.id }) { index, channel ->
      ChannelItem(index = index, channel = channel, onChannelClick = onChannelClick)
    }
  }
}

@Composable
private fun ChannelItem(
  index: Int,
  channel: Channel,
  onChannelClick: (Int, Channel) -> Unit,
) {
  Box(
    modifier = Modifier
      .fillMaxWidth()
      .clickable { onChannelClick.invoke(index, channel) },
  ) {
    ListItem(
      modifier = Modifier.fillMaxWidth(),
      colors = ListItemDefaults.colors(containerColor = AIChatTheme.colors.itemContent),
      leadingContent = {
        Image(
          modifier = Modifier
            .align(Alignment.CenterStart)
            .clip(CircleShape)
            .size(42.dp),
          painter = painterResource(com.ironmeerkat.athena.core.designsystem.R.drawable.ic_gemini),
          contentDescription = null,
        )
      },
      headlineContent = {
        Text(
          text = "Channel${channel.id.take(3)}",
          fontSize = 18.sp,
          fontWeight = FontWeight.Bold,
          color = AIChatTheme.colors.textHighEmphasis,
        )
      },
      supportingContent = {
        Text(
          text = channel.messages.last().message,
          fontSize = 14.sp,
          color = AIChatTheme.colors.textLowEmphasis,
          overflow = TextOverflow.Ellipsis,
          maxLines = 2,
        )
      },
    )

    HorizontalDivider()
  }
}

@Composable
private fun BoxScope.ChannelFloatingButton(
  channelSize: Int,
  channelsViewModel: ChannelsViewModel,
) {
  val shouldDisplayBalloon = channelSize == 0

  Balloon(
    modifier = Modifier
      .align(Alignment.BottomEnd)
      .padding(32.dp)
      .size(58.dp),
    builder = rememberFloatingBalloon(),
    balloonContent = {
      Text(
        modifier = Modifier.padding(horizontal = 12.dp),
        text = "Create a channel and ask anything!",
        textAlign = TextAlign.Center,
        color = Color.White,
      )
    },
  ) { balloonWindow ->
    LaunchedEffect(key1 = Unit) {
      if (shouldDisplayBalloon) {
        balloonWindow.showAlignTop()
      }

      balloonWindow.setOnBalloonDismissListener {
        balloonWindow.dismiss()
      }
    }

    FloatingActionButton(
      onClick = { channelsViewModel.handleEvents(ChannelsEvent.CreateChannel) },
    ) {
      Icon(
        imageVector = Icons.Default.Add,
        tint = AIChatTheme.colors.primary,
        contentDescription = null,
      )
    }
  }
}

@AIChatPreview
@Composable
private fun ChannelPreview() {
  AIChatTheme {
    Column(modifier = Modifier.background(AIChatTheme.colors.background)) {
      ChannelAppBar()

      ChannelContentBody(
        channels = MockUtils.channelList,
        onChannelClick = { _, _ -> },
      )
    }
  }
}
