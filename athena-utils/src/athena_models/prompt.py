from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
import enum

from .utils import Base, TimestampMixin

class PromptRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class Prompt(TimestampMixin, Base):
    __tablename__ = "prompts"
    __table_args__ = (
        sa.UniqueConstraint("key", "version", name="uq_prompts_key_version"),
        sa.Index("prompts_key_idx", "key"),
        sa.Index("prompts_is_active_idx", "is_active"),
        {"schema": "graph"},
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    title: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("1"))
    role: Mapped[PromptRole] = mapped_column(sa.Enum(PromptRole), nullable=False)

    # Additional metadata (template variables, parameters, topic keys, prompt_type, etc.)
    prompt_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))

    # Configuration for LangChain message creation
    message_config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{\"skip_storage\": true}'::jsonb"))

    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("true"))

    def __repr__(self) -> str:
        return f"Prompt(id={self.id!r}, key={self.key!r}, version={self.version!r})"
