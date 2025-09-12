"""Initial database schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-09-12 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

try:
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover
    Vector = None  # type: ignore

try:
    from geoalchemy2 import Geography
except Exception:  # pragma: no cover
    Geography = None  # type: ignore


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure required extensions exist
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "postgis";')

    # Ensure required schemas exist
    op.execute("CREATE SCHEMA IF NOT EXISTS rag;")
    op.execute("CREATE SCHEMA IF NOT EXISTS graph;")

    # api_user
    op.create_table(
        "api_user",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=150), nullable=False, unique=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("phone", sa.String(length=15), nullable=True),
        sa.Column("device_token", sa.String(length=255), nullable=True),
        sa.Column("extension_client_id", sa.String(length=255), nullable=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=True, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_staff", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("date_joined", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # chat
    op.create_table(
        "chat",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("is_telegram", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["api_user.id"], name="fk_chat_user_id_api_user", ondelete="SET NULL"),
    )

    # chat_message
    op.create_table(
        "chat_message",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["chat_id"], ["chat.id"], name="fk_chat_message_chat_id_chat", ondelete="CASCADE"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_message_role_valid"),
    )

    # graph.store
    op.create_table(
        "store",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("prefix", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ttl_minutes", sa.Integer(), nullable=True),
        sa.UniqueConstraint("prefix", "key", name="uq_store_prefix_key"),
        schema="graph",
    )
    op.create_index("store_prefix_idx", "store", ["prefix"], schema="graph")

    # graph.store_vectors
    op.create_table(
        "store_vectors",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("prefix", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536) if Vector else sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("prefix", "key", "field_name", name="uq_store_vectors_prefix_key_field"),
        schema="graph",
    )
    op.create_index("store_vectors_prefix_idx", "store_vectors", ["prefix"], schema="graph")

    # rag.docs
    op.create_table(
        "docs",
        sa.Column("langchain_id", sa.Text(), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536) if Vector else sa.LargeBinary(), nullable=False),
        sa.Column("langchain_metadata", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("title", sa.String(length=200), nullable=True),
        schema="rag",
    )
    # HNSW index for vector similarity (pgvector >= 0.5). If not available, switch to IVFFlat.
    try:
        op.create_index(
            "docs_emb_l2_hnsw",
            "docs",
            ["embedding"],
            schema="rag",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_l2_ops"},
            postgresql_with={"m": 16, "ef_construction": 64},
        )
    except Exception:
        # Fallback for older pgvector versions
        op.create_index(
            "docs_emb_l2_hnsw",
            "docs",
            ["embedding"],
            schema="rag",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_l2_ops"},
            postgresql_with={"lists": 100},
        )

    # digital wellbeing
    op.create_table(
        "digital_wellbeing_location",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("radius", sa.Float(), nullable=False),
        sa.Column("coordinates", Geography(geometry_type="POINT", srid=4326) if Geography else sa.Text(), nullable=False),
    )

    op.create_table(
        "digital_wellbeing_timeframe",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "digital_wellbeing_policy",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("blocked_urls", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("blocked_apps", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("block_shorts", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("whitelisted_urls", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("whitelisted_apps", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )

    op.create_table(
        "digital_wellbeing_schedule",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("policy_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["policy_id"], ["digital_wellbeing_policy.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "digital_wellbeing_schedule_timeframes",
        sa.Column("schedule_id", sa.BigInteger(), nullable=False),
        sa.Column("timeframe_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["digital_wellbeing_schedule.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["timeframe_id"], ["digital_wellbeing_timeframe.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("schedule_id", "timeframe_id"),
    )

    op.create_table(
        "digital_wellbeing_schedule_locations",
        sa.Column("schedule_id", sa.BigInteger(), nullable=False),
        sa.Column("location_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["digital_wellbeing_schedule.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["digital_wellbeing_location.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("schedule_id", "location_id"),
    )


def downgrade() -> None:
    # Drop digital wellbeing association tables first
    op.drop_table("digital_wellbeing_schedule_locations")
    op.drop_table("digital_wellbeing_schedule_timeframes")
    op.drop_table("digital_wellbeing_schedule")
    op.drop_table("digital_wellbeing_policy")
    op.drop_table("digital_wellbeing_timeframe")
    op.drop_table("digital_wellbeing_location")

    # Drop rag.docs index and table
    with op.batch_alter_table("docs", schema="rag"):
        pass
    try:
        op.drop_index("docs_emb_l2_hnsw", table_name="docs", schema="rag")
    except Exception:
        # ignore if already gone
        pass
    op.drop_table("docs", schema="rag")

    # Drop graph tables
    op.drop_index("store_vectors_prefix_idx", table_name="store_vectors", schema="graph")
    op.drop_table("store_vectors", schema="graph")

    op.drop_index("store_prefix_idx", table_name="store", schema="graph")
    op.drop_table("store", schema="graph")

    # Drop chat tables
    op.drop_table("chat_message")
    op.drop_table("chat")

    # Drop user
    op.drop_table("api_user")

    # Drop custom schemas last
    op.execute("DROP SCHEMA IF EXISTS rag CASCADE;")
    op.execute("DROP SCHEMA IF EXISTS graph CASCADE;")


