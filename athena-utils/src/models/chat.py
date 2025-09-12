from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Chat(TimestampMixin, Base):
    __tablename__ = "chat"

    id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)

    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey("api_user.id", ondelete="SET NULL"), nullable=True
    )
    user: Mapped["User" | None] = relationship("User", back_populates="chats")

    is_telegram: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    telegram_chat_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    title: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"Chat(id={self.id!r})"


class ChatMessage(Base):
    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)

    chat_id: Mapped[str] = mapped_column(
        sa.String(64), sa.ForeignKey("chat.id", ondelete="CASCADE"), nullable=False
    )
    chat: Mapped[Chat] = relationship("Chat", back_populates="messages")

    role: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    __table_args__ = (
        sa.CheckConstraint(
            "role IN ('user', 'assistant')", name="ck_chat_message_role_valid"
        ),
    )

    __mapper_args__ = {
        "order_by": (created_at.asc(), id.asc()),
    }

    def __repr__(self) -> str:
        return f"ChatMessage(chat_id={self.chat_id!r}, role={self.role!r})"


