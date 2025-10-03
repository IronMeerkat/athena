from langchain_openai import ChatOpenAI
from pydantic import Field
from prompts import DEFAULT_TELEGRAM_MESSAGES
from utils import BaseUtilityState, MsgFieldType, BaseModel
from langgraph.prebuilt import create_react_agent
from athena_logging import get_logger


logger = get_logger(__name__)

lite_model = ChatOpenAI(model="gpt-5-mini", temperature=0.4, reasoning_effort="low", verbosity="low")

class ToneResponse(BaseModel):
    temperature: float = Field(default=1, ge=0.6, le=1.4)
    reasoning_effort: str = Field(default="medium", choices=["minimal", "low", "medium", "high"])
    verbosity: str = Field(default="medium", choices=["low", "medium", "high"])

class ToneSettings(BaseUtilityState):
    messages: MsgFieldType = Field(default_factory=lambda: DEFAULT_TELEGRAM_MESSAGES) # PLACEHOLDER FOR TONE PROMPT
    temperature: float = Field(default=1, ge=0.6, le=1.4)
    reasoning_effort: str = Field(default="medium", choices=["minimal", "low", "medium", "high"])
    verbosity: str = Field(default="medium", choices=["low", "medium", "high"])

lite_agent = create_react_agent(lite_model, tools=[], response_format=ToneResponse)


async def determine_tone(state: ToneSettings) -> ToneResponse:
    state = ToneSettings.from_other_state(state)
    response = await lite_agent.ainvoke(state)
    response = response['structured_response']
    state.messages.clear()
    return response