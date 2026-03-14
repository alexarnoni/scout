from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TeamMatchStats(Base, TimestampMixin):
    __tablename__ = "team_match_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"), nullable=False
    )
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False)
    goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    possession: Mapped[float | None] = mapped_column(Float, nullable=True)
    shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    red_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xg: Mapped[float | None] = mapped_column(Float, nullable=True)

    match: Mapped["Match"] = relationship(back_populates="team_stats")
    team: Mapped["Team"] = relationship(back_populates="team_match_stats")

    __table_args__ = (
        Index("ix_team_match_stats_match_id", "match_id"),
        Index("ix_team_match_stats_team_id", "team_id"),
        UniqueConstraint(
            "match_id", "team_id", name="uq_team_match_stats_match_team"
        ),
    )
