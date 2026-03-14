from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SourceIdsMixin, TimestampMixin


class Player(Base, TimestampMixin, SourceIdsMixin):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shirt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_ids: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(80), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_foot: Mapped[str | None] = mapped_column(String(20), nullable=True)

    team: Mapped["Team"] = relationship(back_populates="players")
    rosters: Mapped[list["Roster"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )
    match_stats: Mapped[list["PlayerMatchStats"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_players_team_id", "team_id"),)
