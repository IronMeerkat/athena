from __future__ import annotations

from typing import List, TypedDict

from langgraph.graph import END, StateGraph
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from athena_server.config import Settings
from athena_server.memory.vectorstore import get_retriever, get_vectorstore
from athena_server.agents.registry import REGISTRY, AgentConfig, AgentEntry
from athena_server.config import make_embeddings


class AgentState(TypedDict):
    question: str
    context_docs: List[str]
    answer: str


def build_graph(settings: Settings, llm: BaseChatModel) -> StateGraph:
    embeddings = make_embeddings(settings)
    vs = get_vectorstore(settings, embeddings)
    retriever = get_retriever(vs, k=4)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are Athena. Answer grounded in the provided context. If unsure, say you don't know."),
            ("human", "Question: {question}\n\nContext:\n{context}\n\nAnswer concisely."),
        ]
    )

    def retrieve(state: AgentState) -> AgentState:
        docs = retriever.invoke(state["question"])  # type: ignore[index]
        state["context_docs"] = [d.page_content for d in docs]  # type: ignore[index]
        return state

    def generate(state: AgentState) -> AgentState:
        context = "\n---\n".join(state.get("context_docs", []))
        chain = prompt | llm
        out = chain.invoke({"question": state["question"], "context": context})
        state["answer"] = out.content  # type: ignore[index]
        return state

    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph


# Register example agent with a specific model override
REGISTRY.register(
    "example_rag",
    AgentEntry(
        config=AgentConfig(
            name="Example RAG Agent",
            description="Retrieval-augmented QA over ingested documents",
            model_name="gpt-4o-mini",  # override per-agent
        ),
        build_graph=build_graph,
    ),
)
