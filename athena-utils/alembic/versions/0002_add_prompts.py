"""Add prompts table

Revision ID: 0002_add_prompts
Revises: 0001_initial
Create Date: 2025-09-19 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "0002_add_prompts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create prompts table
    op.create_table(
        "prompts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("role", sa.Enum('USER', 'ASSISTANT', 'SYSTEM', 'TOOL', name='promptrole'), nullable=False),
        sa.Column("prompt_metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("message_config", JSONB, nullable=False, server_default=sa.text("'{\"skip_storage\": true}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        schema="graph",
    )

    # Create indexes
    op.create_index("prompts_key_idx", "prompts", ["key"], schema="graph")
    op.create_index("prompts_is_active_idx", "prompts", ["is_active"], schema="graph")

    # Create unique constraint on key + version
    op.create_unique_constraint("uq_prompts_key_version", "prompts", ["key", "version"], schema="graph")


def downgrade() -> None:
    # Drop table and indexes
    op.drop_table("prompts", schema="graph")
    op.execute("DROP TYPE IF EXISTS promptrole")
