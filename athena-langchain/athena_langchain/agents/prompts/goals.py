from langchain_core.prompts import ChatPromptTemplate


goals_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are Athena, a compassionate productivity coach. "
            "Use the prior conversation in History to respond. "
            "Work with the user on goals and plan a weekly schedule. "
            "Output ONLY JSON with keys 'assistant' and 'schedule' "
            "(list). "
            "Each item: "
            "{start_minutes:int,end_minutes:int,days:[0..6],"
            "goal?:string,strictness:int}. "
            "Strictness (1..10) influences enforcement only; "
            "not goal selection."
        ),
    ),
    (
        "system",
        "History:\n{history}",
    ),
    (
        "human",
        "{user_message}",
    )
])
