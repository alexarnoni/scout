from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SourceIdsMixin, TimestampMixin


class Competition(Base, TimestampMixin, SourceIdsMixin):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    season: Mapped[str | None] = mapped_column(String(20), nullable=True)

    teams: Mapped[list["Team"]] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )
    rosters: Mapped[list["Roster"]] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )
    matches: Mapped[list["Match"]] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )
