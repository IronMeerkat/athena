from langchain_openai import ChatOpenAI
from pydantic import Field
from polymetis.agents.prompts import SYSTEM_PROMPT_1, TONE_PROMPT
from utils import BaseUtilityState, MsgFieldType
from langgraph.prebuilt import create_react_agent


lite_model = ChatOpenAI(model="gpt-5-mini", temperature=0.4, reasoning_effort="low", verbosity="low")


class ToneSettings(BaseUtilityState):
    messages: MsgFieldType = Field(default_factory=lambda: [SYSTEM_PROMPT_1, TONE_PROMPT])
    temperature: float = Field(default=0.4, ge=0.6, le=1.4)
    reasoning_effort: str = Field(default="medium", choices=["minimal", "low", "medium", "high"])
    verbosity: str = Field(default="medium", choices=["low", "medium", "high"])

lite_agent = create_react_agent(lite_model, state_schema=ToneSettings)


async def determine_tone(state: ToneSettings) -> ToneSettings:
    state = state.from_other_state(state)
    return await lite_agent.ainvoke(state)