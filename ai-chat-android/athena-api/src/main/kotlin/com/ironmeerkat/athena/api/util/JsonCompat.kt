package com.ironmeerkat.athena.api.util

import kotlinx.serialization.json.JsonPrimitive

/**
 * Backport convenience: Kotlinx 1.6+ offers contentOrNull; provide our own to avoid unresolved refs.
 */
val JsonPrimitive.contentOrNull: String?
  get() = try {
    this.content
  } catch (_: Throwable) {
    null
  }



