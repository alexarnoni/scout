from __future__ import annotations

from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SourceIdsMixin, TimestampMixin


class Team(Base, TimestampMixin, SourceIdsMixin):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_ids: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)

    competition: Mapped["Competition"] = relationship(back_populates="teams")
    staff_members: Mapped[list["Staff"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    players: Mapped[list["Player"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    rosters: Mapped[list["Roster"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    home_matches: Mapped[list["Match"]] = relationship(
        back_populates="home_team", foreign_keys="Match.home_team_id"
    )
    away_matches: Mapped[list["Match"]] = relationship(
        back_populates="away_team", foreign_keys="Match.away_team_id"
    )
    team_match_stats: Mapped[list["TeamMatchStats"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    player_match_stats: Mapped[list["PlayerMatchStats"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_teams_competition_id", "competition_id"),)
