from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import Field, field_validator
from prompts import DEFAULT_TELEGRAM_MESSAGES
from utils import BaseUtilityState, MsgFieldType, BaseModel
from typing import List
from typing_extensions import Literal
from langgraph.prebuilt import create_react_agent
from athena_logging import get_logger

logger = get_logger(__name__)

lite_model = ChatOpenAI(model="gpt-5-mini", temperature=0.4, reasoning_effort="low", verbosity="low")

TopicLiteral = Literal["philosophy", "political", "foreign_policy", "science"]

class TopicSettings(BaseUtilityState):
    messages: MsgFieldType = Field(default_factory=lambda: DEFAULT_TELEGRAM_MESSAGES) # PLACEHOLDER FOR TOPIC PROMPT
    topics: List[TopicLiteral] = Field(default_factory=list)


class TopicResponse(BaseModel):
    topics: List[TopicLiteral]

lite_agent = create_react_agent(lite_model, response_format=TopicResponse, tools=[])

async def determine_topics(state: TopicSettings) -> TopicResponse:
    state = TopicSettings.from_other_state(state)
    response = await lite_agent.ainvoke(state)
    response = response['structured_response']
    state.messages.clear()
    logger.info(f"state: {response}")
    return response