"""camada 3 sync keys

Revision ID: c7d8e9f0a1b2
Revises: b3c4d5e6f7a8
Create Date: 2026-01-07 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c7d8e9f0a1b2"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("external_source", sa.String(length=50), nullable=True))
    op.add_column("matches", sa.Column("external_id", sa.String(length=100), nullable=True))
    op.add_column("matches", sa.Column("external_ids", sa.JSON(), nullable=True))
    op.create_unique_constraint(
        "uq_matches_external_source_id",
        "matches",
        ["external_source", "external_id"],
    )

    op.create_unique_constraint(
        "uq_team_match_stats_match_team",
        "team_match_stats",
        ["match_id", "team_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_team_match_stats_match_team",
        "team_match_stats",
        type_="unique",
    )
    op.drop_constraint(
        "uq_matches_external_source_id",
        "matches",
        type_="unique",
    )
    op.drop_column("matches", "external_ids")
    op.drop_column("matches", "external_id")
    op.drop_column("matches", "external_source")
