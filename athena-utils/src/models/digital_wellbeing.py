from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

try:
    from geoalchemy2 import Geography, WKTElement
except Exception as e:  # pragma: no cover
    raise

from .base import Base


class Location(Base):
    __tablename__ = "digital_wellbeing_location"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    radius: Mapped[float] = mapped_column(sa.Float, nullable=False)
    coordinates = sa.Column(Geography(geometry_type="POINT", srid=4326), nullable=False)

    schedules: Mapped[list["Schedule"]] = relationship(
        back_populates="locations", secondary="digital_wellbeing_schedule_locations"
    )


class TimeFrame(Base):
    __tablename__ = "digital_wellbeing_timeframe"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    day_of_week: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    start: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    end: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    schedules: Mapped[list["Schedule"]] = relationship(
        back_populates="time_frames", secondary="digital_wellbeing_schedule_timeframes"
    )


class Policy(Base):
    __tablename__ = "digital_wellbeing_policy"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    blocked_urls: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))
    blocked_apps: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))
    block_shorts: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("false"))
    whitelisted_urls: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))
    whitelisted_apps: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))

    schedules: Mapped[list["Schedule"]] = relationship("Schedule", back_populates="policy")


# Association tables for many-to-many
schedule_timeframes = sa.Table(
    "digital_wellbeing_schedule_timeframes",
    Base.metadata,
    sa.Column("schedule_id", sa.BigInteger, sa.ForeignKey("digital_wellbeing_schedule.id", ondelete="CASCADE"), primary_key=True),
    sa.Column("timeframe_id", sa.BigInteger, sa.ForeignKey("digital_wellbeing_timeframe.id", ondelete="CASCADE"), primary_key=True),
)

schedule_locations = sa.Table(
    "digital_wellbeing_schedule_locations",
    Base.metadata,
    sa.Column("schedule_id", sa.BigInteger, sa.ForeignKey("digital_wellbeing_schedule.id", ondelete="CASCADE"), primary_key=True),
    sa.Column("location_id", sa.BigInteger, sa.ForeignKey("digital_wellbeing_location.id", ondelete="CASCADE"), primary_key=True),
)


class Schedule(Base):
    __tablename__ = "digital_wellbeing_schedule"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(
        sa.BigInteger, sa.ForeignKey("digital_wellbeing_policy.id", ondelete="CASCADE"), nullable=False
    )
    policy: Mapped[Policy] = relationship("Policy", back_populates="schedules")

    time_frames: Mapped[list[TimeFrame]] = relationship(
        "TimeFrame", secondary="digital_wellbeing_schedule_timeframes", back_populates="schedules"
    )
    locations: Mapped[list[Location]] = relationship(
        "Location", secondary="digital_wellbeing_schedule_locations", back_populates="schedules"
    )


