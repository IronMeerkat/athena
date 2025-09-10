from langchain_core.prompts import ChatPromptTemplate


classify_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are a focused productivity classifier. "
            "Given a page host/path/title or an Android package/activity, "
            "choose exactly one classification from this set:\n"
            "- work\n- neutral\n- distraction\n- unhealthy_habit\n\n"
            "Use the provided strictness (1..10) as your bias towards "
            "blocking: 10=extremely strict, 1=very lenient.\n"
            "Also consider the current timeblock goal. If the page/app "
            "does not align with the goal, prefer 'distraction' "
            "at high strictness.\n"
            "Return ONLY valid JSON shaped as:"
            " {{\"classification\": "
            "\"work|neutral|distraction|unhealthy_habit\"}}."
        ),
    ),
    (
        "system",
        "Optional external CONTEXT (may be empty):\n{context}",
    ),
    (
        "human",
        (
            "strictness={strictness}\n"
            "timeblock_goal={timeblock_goal}\n"
            "host={host}\n"
            "app={app}\n"
            "path={path}\n"
            "activity={activity}\n"
            "title={title}"
        ),
    ),
])


appeals_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are Athena, acting as a fair but firm productivity "
            "coach. You are evaluating a user's appeal to allow "
            "temporary access. Consider strictness (1..10) and the "
            "current timeblock goal. Be lenient at low strictness and "
            "strict at high strictness, but always explain. Return ONLY "
            "JSON with: {\"assistant\":string,\"allow\":boolean,"
            "\"minutes\":number}. "
            "If allowing, minutes should be minimal (1-60)."
        ),
    ),
    (
        "system",
        "Optional external CONTEXT (may be empty):\n{context}",
    ),
    (
        "system",
        (
            "Context: strictness={strictness} | goal={goal} | "
            "host={host} path={path} title={title} "
            "package={package} activity={activity}"
        ),
    ),
    (
        "human",
        (
            "User justification: {user_justification}\n"
            "Requested minutes: {requested_minutes}"
        ),
    ),
])
