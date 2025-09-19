"""merge_prompts_and_sqlalchemy

Revision ID: 3623834d8322
Revises: 0002_add_prompts, 03d9101302f1
Create Date: 2025-09-19 18:48:44.722149
"""

from __future__ import annotations

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision = "3623834d8322"
down_revision = ('0002_add_prompts', '03d9101302f1')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass


