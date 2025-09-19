from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from athena_settings import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Ensure "src" is on sys.path so we can import models
# This works both from athena-utils directory and from root directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # athena-utils directory
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from athena_models.utils import Base  # noqa: E402
# Import models so tables are registered in metadata for autogenerate
import athena_models.user  # noqa: F401,E402
import athena_models.chat  # noqa: F401,E402
import athena_models.doc  # noqa: F401,E402
import athena_models.store  # noqa: F401,E402
import athena_models.digital_wellbeing  # noqa: F401,E402

target_metadata = Base.metadata


def get_url() -> str:
    return settings.DATABASE_URL


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


