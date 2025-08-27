package nethical.digipaws.ai

/**
 * Core AI Agent models and abstractions.
 */

/**
 * Lightweight context passed to agents during evaluation.
 * Can be extended over time without breaking implementers.
 */
data class AgentContext(
    val currentTimeMillis: Long = System.currentTimeMillis()
)

/**
 * Represents a suggestion or recommendation surfaced by an Agent.
 */
data class AgentSuggestion(
    val id: String,
    val title: String,
    val message: String,
    val priority: Priority = Priority.NORMAL,
    val sourceAgentId: String,
    val tags: Set<String> = emptySet()
) {
    enum class Priority {
        LOW, NORMAL, HIGH, CRITICAL
    }
}

/**
 * Agents analyze device/app state and surface suggestions.
 */
interface Agent {
    val id: String
    val displayName: String
    val description: String

    fun evaluate(context: AgentContext): List<AgentSuggestion>
}


