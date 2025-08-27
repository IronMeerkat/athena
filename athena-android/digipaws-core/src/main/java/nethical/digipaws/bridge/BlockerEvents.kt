package nethical.digipaws.bridge

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow

sealed class BlockerEvent {
  data class Block(val reason: String) : BlockerEvent()
  data class Nudge(val eventId: String, val ttlMinutes: Int) : BlockerEvent()
}

object BlockerEvents {
  private val _events = MutableSharedFlow<BlockerEvent>(extraBufferCapacity = 64)
  val events = _events.asSharedFlow()

  fun emit(event: BlockerEvent) {
    _events.tryEmit(event)
  }
}


