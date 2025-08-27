package nethical.digipaws.ai

/** Decision and appeals models for distraction detection. */

enum class DecisionOutcome { ALLOW, BLOCK, ASK_APPEAL }

data class UsageSnapshot(
    val lastHourMs: Long = 0,
    val todayMs: Long = 0,
    val sessionsToday: Int = 0
)

data class DecisionRequest(
    val packageName: String,
    val timestamp: Long = System.currentTimeMillis(),
    val latitude: Double? = null,
    val longitude: Double? = null,
    val usage: UsageSnapshot? = null
)

data class DecisionResult(
    val outcome: DecisionOutcome,
    val reason: String,
    val recommendedMinutes: Int? = null
)

interface DecisionAgent {
    val id: String
    fun decide(request: DecisionRequest, context: AgentContext = AgentContext()): DecisionResult
}

interface AppealsAgent {
    val id: String
    fun evaluateAppeal(
        request: DecisionRequest,
        userJustification: String,
        requestedMinutes: Int,
        context: AgentContext = AgentContext()
    ): DecisionResult
}


