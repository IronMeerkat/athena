"""migrate to sqlalchemy

Revision ID: 03d9101302f1
Revises: 0001_initial
Create Date: 2025-09-16 22:44:59.916080
"""

from __future__ import annotations

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision = "03d9101302f1"
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


