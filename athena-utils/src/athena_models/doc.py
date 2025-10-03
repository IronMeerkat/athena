from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector


from .utils import Base


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

    # Foreign key to User
    user_id: Mapped[int] = mapped_column(sa.BigInteger, sa.ForeignKey("api_user.id"), nullable=False)

    # Relationship to User
    user: Mapped["User"] = relationship("User", back_populates="docs")


