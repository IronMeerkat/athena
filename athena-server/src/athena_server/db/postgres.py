from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from athena_server.config import Settings


def get_engine(settings: Settings) -> Engine:
    engine = create_engine(settings.postgres_dsn, pool_pre_ping=True, future=True)
    return engine


def ensure_extensions(engine: Engine) -> None:
    # Ensure pgvector exists. docker init script should create it, but this is idempotent.
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
