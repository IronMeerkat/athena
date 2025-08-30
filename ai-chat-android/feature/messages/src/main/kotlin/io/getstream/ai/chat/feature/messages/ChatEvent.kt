package com.ironmeerkat.athena.feature.messages

/**
 * UI-level events for the Messages screen.
 * - SendMessage: user submitted a message.
 * - CompleteGeneration: model finished generating a response; persist it.
 */
sealed interface ChatEvent {

  data object Nothing : ChatEvent

  data class SendMessage(val message: String, val sender: String) : ChatEvent

  data class CompleteGeneration(val message: String, val sender: String) : ChatEvent
}


