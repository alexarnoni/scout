from __future__ import annotations

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SourceIdsMixin, TimestampMixin


class Roster(Base, TimestampMixin, SourceIdsMixin):
    __tablename__ = "rosters"

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"), nullable=False
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"), nullable=False
    )

    competition: Mapped["Competition"] = relationship(back_populates="rosters")
    team: Mapped["Team"] = relationship(back_populates="rosters")
    player: Mapped["Player"] = relationship(back_populates="rosters")

    __table_args__ = (
        Index("ix_rosters_competition_id", "competition_id"),
        Index("ix_rosters_team_id", "team_id"),
    )
