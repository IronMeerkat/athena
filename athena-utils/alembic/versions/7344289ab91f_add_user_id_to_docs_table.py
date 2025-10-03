"""add_user_id_to_docs_table

Revision ID: 7344289ab91f
Revises: 3623834d8322
Create Date: 2025-09-24 21:23:23.378579
"""

from __future__ import annotations

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision = "7344289ab91f"
down_revision = '3623834d8322'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id column to rag.docs table
    op.add_column(
        "docs",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        schema="rag"
    )

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_docs_user_id_api_user",
        "docs",
        "api_user",
        ["user_id"],
        ["id"],
        source_schema="rag",
        referent_schema=None
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint(
        "fk_docs_user_id_api_user",
        "docs",
        type_="foreignkey",
        schema="rag"
    )

    # Drop user_id column
    op.drop_column("docs", "user_id", schema="rag")


