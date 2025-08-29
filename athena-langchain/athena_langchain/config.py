from __future__ import annotations
import urllib.parse as urlparse
import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

DATABASE_URL = os.getenv("DATABASE_URL")
db_parsed = urlparse.urlparse(DATABASE_URL)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class Settings(BaseSettings):
    # Server (kept for parity; not used directly by workers)
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Postgres
    postgres_host: str = db_parsed.hostname or "localhost"
    postgres_port: int = db_parsed.port or 5432
    postgres_db: str = db_parsed.path.lstrip("/")
    postgres_user: str = db_parsed.username or ""
    postgres_password: str = db_parsed.password or ""

    # Vector config
    vector_table_name: str = "athena_embeddings"
    vector_collection: str = "athena"

    # Redis
    redis_url: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

    # LLM + Embeddings (defaults; can be overridden per-agent)
    llm_provider: str = "openai"  # openai or ollama
    llm_model: str = "gpt-5-mini"  # per-agent overrides take precedence
    embeddings_provider: str = "openai"
    openai_api_key: Optional[str] = OPENAI_API_KEY
    ollama_base_url: str = "http://localhost:11434"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# ---- Factories for LLMs and Embeddings ----

def make_llm(
    settings: Settings,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
):
    eff_provider = (provider or settings.llm_provider).lower()
    eff_model = model or settings.llm_model
    eff_temperature = 0.0 if temperature is None else float(temperature)
    if eff_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=eff_model, api_key=settings.openai_api_key, temperature=eff_temperature)
    elif eff_provider == "ollama":
        from langchain_community.chat_models.ollama import ChatOllama

        return ChatOllama(model=eff_model, base_url=settings.ollama_base_url, temperature=eff_temperature)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {eff_provider}")


def make_embeddings(settings: Settings):
    provider = settings.embeddings_provider.lower()
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        # Choose a default; override via OPENAI_EMBEDDINGS_MODEL if desired later
        return OpenAIEmbeddings(model="text-embedding-3-small", api_key=settings.openai_api_key)
    elif provider == "ollama":
        from langchain_community.embeddings.ollama import OllamaEmbeddings

        return OllamaEmbeddings(model="nomic-embed-text", base_url=settings.ollama_base_url)
    else:
        raise ValueError(f"Unsupported EMBEDDINGS_PROVIDER: {settings.embeddings_provider}")


