package com.ironmeerkat.athena.core.logging

import timber.log.Timber

/**
 * Timber tree that prefixes tags with a module name based on the caller's package.
 * Example: "core:network/MyClass" or "feature:messages/ChatViewModel".
 */
internal class ModuleTaggedDebugTree : Timber.DebugTree() {
  override fun createStackElementTag(element: StackTraceElement): String {
    val base = super.createStackElementTag(element)
    val module = deriveModuleName(element.className)
    return "$module/$base"
  }

  private fun deriveModuleName(className: String): String {
    // Expecting packages like com.ironmeerkat.athena.<module>....
    val parts = className.split('.')
    val index = parts.indexOfFirst { it == "athena" }
    if (index >= 0) {
      val next = parts.getOrNull(index + 1)
      // If the next token is missing or looks like a class name (starts uppercase), treat as app
      if (next.isNullOrBlank() || next.firstOrNull()?.isUpperCase() == true) {
        return "app"
      }
      // normalize common prefixes to compact module label
      return when (next) {
        "core" -> {
          val sub = parts.getOrNull(index + 2)
          if (sub != null) "core:$sub" else "core"
        }
        "feature" -> {
          val sub = parts.getOrNull(index + 2)
          if (sub != null) "feature:$sub" else "feature"
        }
        else -> next
      }
    }
    return "app"
  }
}


