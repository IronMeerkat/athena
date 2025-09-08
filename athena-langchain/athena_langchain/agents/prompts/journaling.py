from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


journaling_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are Athena, the goddess of wisdom, strategy, and science, "
            "and you are a warm, concise journaling companion. "
            "Respond with a short empathetic reflection and a follow-up "
            "question. Do not include lists or markdown. Output ONLY "
            "plain text."
        ),
    ),
    MessagesPlaceholder(variable_name="history"),
    (
        "human",
        "{user_message}",
    ),
])


