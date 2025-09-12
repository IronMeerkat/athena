from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

try:
    from pgvector.sqlalchemy import Vector
except Exception as e:  # pragma: no cover
    # Defer import errors to runtime where environment may differ
    raise

from .base import Base


class Doc(Base):
    __tablename__ = "docs"
    __table_args__ = {
        "schema": "rag",
        # HNSW index will be created via Alembic migration (vendor-specific)
    }

    # Mirrors langchain PGVectorStore defaults
    langchain_id: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    embedding = sa.Column(Vector(1536), nullable=False)
    langchain_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))

    title: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)


