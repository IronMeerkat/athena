from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Server
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Postgres
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "athena"
    postgres_user: str = "athena"
    postgres_password: str = "athena"

    # Vector config
    vector_table_name: str = "athena_embeddings"
    vector_collection: str = "athena"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM + Embeddings
    llm_provider: str = "openai"  # openai or ollama
    llm_model: str = "gpt-4o-mini"
    embeddings_provider: str = "openai"
    openai_api_key: Optional[str] = None
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

def make_llm(settings: Settings):
    provider = settings.llm_provider.lower()
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.llm_model, api_key=settings.openai_api_key, temperature=0)
    elif provider == "ollama":
        from langchain_community.chat_models.ollama import ChatOllama

        return ChatOllama(model=settings.llm_model, base_url=settings.ollama_base_url, temperature=0)
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


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
