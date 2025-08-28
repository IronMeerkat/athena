package com.ironmeerkat.athena.chat.model

enum class Sender { USER, ASSISTANT }

data class UiMessage(
  val id: String,
  val sender: Sender,
  val text: String,
  val timestampMs: Long
)


