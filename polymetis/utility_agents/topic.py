from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import Field, field_validator
from polymetis.agents.prompts import TOPIC_PROMPT_DICT, SYSTEM_PROMPT_1, TOPIC_PROMPT
from utils import BaseUtilityState, MsgFieldType
from typing import List
from typing_extensions import Literal
from langgraph.prebuilt import create_react_agent

lite_model = ChatOpenAI(model="gpt-5-mini", temperature=0.4, reasoning_effort="low", verbosity="low")

TopicLiteral = Literal["philosophy", "political", "foreign_policy", "science"]

class TopicSettings(BaseUtilityState):
    messages: MsgFieldType = Field(default_factory=lambda: [SYSTEM_PROMPT_1, TOPIC_PROMPT])
    topics: List[TopicLiteral] = Field(
        default_factory=list,
        description="List of topic keys from TOPIC_PROMPT_DICT",
        min_items=0,
        max_items=len(TOPIC_PROMPT_DICT)
    )


lite_agent = create_react_agent(lite_model, state_schema=TopicSettings, tools=[])

async def determine_topics(state: TopicSettings) -> TopicSettings:
    state = state.from_other_state(state)
    return await lite_agent.ainvoke(state)