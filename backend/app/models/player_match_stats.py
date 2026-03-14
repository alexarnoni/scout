from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class PlayerMatchStats(Base, TimestampMixin):
    __tablename__ = "player_match_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id"), nullable=False
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"), nullable=False
    )
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assists: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    key_passes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pass_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    tackles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interceptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duels_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fouls_committed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    yellow_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    red_cards: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    xa: Mapped[float | None] = mapped_column(Float, nullable=True)

    match: Mapped["Match"] = relationship(back_populates="player_stats")
    player: Mapped["Player"] = relationship(back_populates="match_stats")
    team: Mapped["Team"] = relationship(back_populates="player_match_stats")

    __table_args__ = (
        Index("ix_player_match_stats_match_id", "match_id"),
        Index("ix_player_match_stats_player_id", "player_id"),
        UniqueConstraint(
            "match_id", "player_id", name="uq_player_match_stats_match_player"
        ),
    )
