from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "api_user"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)

    username: Mapped[str] = mapped_column(sa.String(150), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(sa.String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(sa.String(15), nullable=True)
    device_token: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    extension_client_id: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)

    telegram_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, unique=True, nullable=True)

    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    is_admin: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    is_staff: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))

    date_joined: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )

    # Relationships
    chats: Mapped[list["Chat"]] = relationship(
        "Chat", back_populates="user", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, username={self.username!r})"


