import asyncio
import datetime
import logging
from typing import List

from sqlalchemy import ForeignKey
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import selectinload
import sqlalchemy as sa
from sqlalchemy.schema import MetaData

from athena_settings import settings
from athena_logging import get_logger


NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at = sa.Column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at = sa.Column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

class Base(AsyncAttrs, DeclarativeBase):
    metadata = metadata


# Configure SQLAlchemy logging to use athena_logger and only log warnings and higher
sqlalchemy_logger = get_logger("sqlalchemy.engine")
sqlalchemy_logger.setLevel(logging.WARNING)

# Create engine without echo, let athena_logger handle it
engine = create_async_engine(settings.DATABASE_URL, echo=False)
db_session = async_sessionmaker(engine, expire_on_commit=False)