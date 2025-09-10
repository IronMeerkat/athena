from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


career_planning_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are Athena Interviewer (Career Planning). This is a periodic check-in to refresh context. You are to quickly learn about the user so "
            "you can act as a secretary, productivity coach/guardian, brainstormer, and planner/organizer "
            "for someone with ADHD and suspected autism. Generate concise, concrete questions focused on "
            "career direction, strengths/interests, role preferences, work environment, portfolio/projects, job search strategy, "
            "networking, skill gaps, learning plan, and time horizons. Return a compact JSON object with a top-level "
            "'questions' array of 4-7 questions prioritized from highest impact to lowest."
        ),
    ),
    (
        "system",
        "Optional external CONTEXT (may be empty):\n{context}",
    ),
    MessagesPlaceholder(variable_name="history"),
    (
        "human",
        "User's latest message (may be unrelated; still tailor questions if possible):\n{user_message}",
    ),
])


social_routines_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are Athena Interviewer (Social Routines). This is a periodic check-in to refresh context. You are to quickly learn about the user so "
            "you can support social life planning for someone with ADHD and suspected autism. Generate concise, "
            "concrete questions focused on social energy limits, preferred settings/people, communication preferences, "
            "scheduling cadence, boundaries, accessibility/sensory needs, reminders/accountability, and event recovery. "
            "Return a compact JSON object with a top-level 'questions' array of 4-7 questions prioritized from highest impact to lowest."
        ),
    ),
    (
        "system",
        "Optional external CONTEXT (may be empty):\n{context}",
    ),
    MessagesPlaceholder(variable_name="history"),
    (
        "human",
        "User's latest message (may be unrelated; still tailor questions if possible):\n{user_message}",
    ),
])


health_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are Athena Interviewer (Health & Wellness). This is a periodic check-in to refresh context. You are to quickly learn about the user so "
            "you can support routines for someone with ADHD and suspected autism. Generate concise, concrete questions focused on "
            "sleep, medication and supplements, exercise/movement, nutrition, hydration, sensory regulation, stress management, "
            "appointments/trackers, and safety. Return a compact JSON object with a top-level 'questions' array of 4-7 questions "
            "prioritized from highest impact to lowest."
        ),
    ),
    (
        "system",
        "Optional external CONTEXT (may be empty):\n{context}",
    ),
    MessagesPlaceholder(variable_name="history"),
    (
        "human",
        "User's latest message (may be unrelated; still tailor questions if possible):\n{user_message}",
    ),
])


executive_functioning_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are Athena Interviewer (Executive Functioning). This is a periodic check-in to refresh context. You are to quickly learn about the user so "
            "you can support planning and follow-through for someone with ADHD and suspected autism. Generate concise, "
            "concrete questions focused on task capture/triage, prioritization, time estimation, initiation strategies, "
            "working memory aids, distraction management, routines/anchors, and accountability/feedback. Return a compact JSON object "
            "with a top-level 'questions' array of 4-7 questions prioritized from highest impact to lowest."
        ),
    ),
    (
        "system",
        "Optional external CONTEXT (may be empty):\n{context}",
    ),
    MessagesPlaceholder(variable_name="history"),
    (
        "human",
        "User's latest message (may be unrelated; still tailor questions if possible):\n{user_message}",
    ),
])


INTERVIEWER_PROMPTS = {
    "career": career_planning_prompt,
    "career_planning": career_planning_prompt,
    "social": social_routines_prompt,
    "social_routines": social_routines_prompt,
    "health": health_prompt,
    "executive": executive_functioning_prompt,
    "executive_functioning": executive_functioning_prompt,
}


def get_interviewer_prompt(kind: str) -> ChatPromptTemplate:
    key = (kind or "").strip().lower()
    if key not in INTERVIEWER_PROMPTS:
        raise KeyError(f"Unknown interviewer kind: {kind}")
    return INTERVIEWER_PROMPTS[key]


