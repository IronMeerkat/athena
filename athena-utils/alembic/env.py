from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Ensure "src" is on sys.path so we can import models
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from models.base import metadata  # noqa: E402
# Import models so tables are registered in metadata for autogenerate
import models.user  # noqa: F401,E402
import models.chat  # noqa: F401,E402
import models.doc  # noqa: F401,E402
import models.store  # noqa: F401,E402
import models.digital_wellbeing  # noqa: F401,E402

target_metadata = metadata


def get_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if url:
        # normalize to psycopg driver
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://") and "+" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url
    # Fallback for local dev if env var isn't present
    return "postgresql+psycopg://localhost/athena"


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        include_schemas=True,
        version_table_schema="public",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_schemas=True,
            version_table_schema="public",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


