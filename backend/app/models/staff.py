from __future__ import annotations

from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SourceIdsMixin, TimestampMixin


class Staff(Base, TimestampMixin, SourceIdsMixin):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_ids: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    team: Mapped["Team"] = relationship(back_populates="staff_members")

    __table_args__ = (Index("ix_staff_team_id", "team_id"),)
