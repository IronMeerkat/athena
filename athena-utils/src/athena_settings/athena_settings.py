from pydantic import create_model
from typing import Any, Dict, Optional, Tuple
import yaml
import importlib.resources
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage


settings_dir = importlib.resources.files(__name__)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(validate_default=False, case_sensitive=True)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

def tuple_to_message(tuple: Tuple[str, str]) -> BaseMessage:
    if tuple[0] == "system":
        return SystemMessage(content=tuple[1])
    elif tuple[0] == "human":
        return HumanMessage(content=tuple[1])
    elif tuple[0] == "ai":
        return AIMessage(content=tuple[1])
    elif tuple[0] == "tool":
        return ToolMessage(content=tuple[1])

def recursive_pydantic_settings_model(data: Dict[str, Any]) -> Settings:
    # Whole dict becomes an attr
    fields = {}

    try:
        for key, value in data.items():
            if isinstance(value, dict):
                fields[key] = (Settings, recursive_pydantic_settings_model(value))
            # elif isinstance(value, list):
            #     fields[key] = (list, [recursive_pydantic_settings_model(item) for item in value])
            else:
                fields[key] = (type(value), value)
    except Exception as e:
        print(f"Error creating settings: {data} {type(data)}")
        raise e

    DynamicModel = create_model("DynamicModel", **fields)
    return DynamicModel()

with open(settings_dir / 'messages.yaml', 'r') as f:
    messages_dict = yaml.full_load(f)

with open(settings_dir / 'settings.yaml', 'r') as f:
    settings_dict = yaml.full_load(f)

messages_dict = {k: tuple_to_message(v) for k, v in messages_dict.items()}

settings_dict["messages"] = messages_dict


settings = recursive_pydantic_settings_model(settings_dict)
