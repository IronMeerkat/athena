from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from pgvector.sqlalchemy import Vector

from .utils import Base


class StoreKV(Base):
    __tablename__ = "store"
    __table_args__ = (
        sa.UniqueConstraint("prefix", "key", name="uq_store_prefix_key"),
        {"schema": "graph"},
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    prefix: Mapped[str] = mapped_column(sa.Text, nullable=False)
    key: Mapped[str] = mapped_column(sa.Text, nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False
    )
    expires_at: Mapped[sa.DateTime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    ttl_minutes: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("prefix", "key", name="uq_store_prefix_key"),
        sa.Index("store_prefix_idx", "prefix"),
        {"schema": "graph"},
    )


class StoreVector(Base):
    __tablename__ = "store_vectors"
    __table_args__ = (
        sa.UniqueConstraint("prefix", "key", "field_name", name="uq_store_vectors_prefix_key_field"),
        sa.Index("store_vectors_prefix_idx", "prefix"),
        {"schema": "graph"},
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    prefix: Mapped[str] = mapped_column(sa.Text, nullable=False)
    key: Mapped[str] = mapped_column(sa.Text, nullable=False)
    field_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    embedding = sa.Column(Vector(1536), nullable=False)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False
    )


