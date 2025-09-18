from pydantic import create_model
from typing import Any, Dict, Optional
import yaml
import importlib.resources
from pydantic_settings import BaseSettings, SettingsConfigDict


settings_file = importlib.resources.files(__name__) / 'settings.yaml'

class Settings(BaseSettings):
    model_config = SettingsConfigDict(validate_default=False, case_sensitive=True)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

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


with open(settings_file, 'r') as f:
    settings_dict = yaml.full_load(f)
settings = recursive_pydantic_settings_model(settings_dict)
