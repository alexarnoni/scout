"""camada 2 fpf fields

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-01-07 22:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b3c4d5e6f7a8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("competitions", sa.Column("season", sa.String(length=20), nullable=True))

    op.add_column("teams", sa.Column("external_ids", sa.JSON(), nullable=True))
    op.add_column("teams", sa.Column("logo_url", sa.String(length=500), nullable=True))
    op.add_column("teams", sa.Column("city", sa.String(length=120), nullable=True))

    op.add_column("players", sa.Column("external_ids", sa.JSON(), nullable=True))
    op.add_column("players", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("players", sa.Column("nationality", sa.String(length=80), nullable=True))
    op.add_column("players", sa.Column("photo_url", sa.String(length=500), nullable=True))
    op.add_column("players", sa.Column("height_cm", sa.Integer(), nullable=True))
    op.add_column("players", sa.Column("preferred_foot", sa.String(length=20), nullable=True))

    op.add_column("staff", sa.Column("external_ids", sa.JSON(), nullable=True))
    op.add_column("staff", sa.Column("photo_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("staff", "photo_url")
    op.drop_column("staff", "external_ids")

    op.drop_column("players", "preferred_foot")
    op.drop_column("players", "height_cm")
    op.drop_column("players", "photo_url")
    op.drop_column("players", "nationality")
    op.drop_column("players", "birth_date")
    op.drop_column("players", "external_ids")

    op.drop_column("teams", "city")
    op.drop_column("teams", "logo_url")
    op.drop_column("teams", "external_ids")

    op.drop_column("competitions", "season")
