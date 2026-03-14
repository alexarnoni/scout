"""camada 3.2 player stats

Revision ID: d1e2f3a4b5c6
Revises: c7d8e9f0a1b2
Create Date: 2026-01-08 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d1e2f3a4b5c6"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("player_match_stats", sa.Column("shots_on_target", sa.Integer(), nullable=True))
    op.add_column("player_match_stats", sa.Column("passes", sa.Integer(), nullable=True))
    op.add_column("player_match_stats", sa.Column("pass_accuracy", sa.Float(), nullable=True))
    op.add_column("player_match_stats", sa.Column("duels_won", sa.Integer(), nullable=True))
    op.add_column("player_match_stats", sa.Column("fouls_committed", sa.Integer(), nullable=True))
    op.add_column("player_match_stats", sa.Column("yellow_cards", sa.Integer(), nullable=True))
    op.add_column("player_match_stats", sa.Column("red_cards", sa.Integer(), nullable=True))
    op.add_column("player_match_stats", sa.Column("rating", sa.Float(), nullable=True))
    op.create_unique_constraint(
        "uq_player_match_stats_match_player",
        "player_match_stats",
        ["match_id", "player_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_player_match_stats_match_player",
        "player_match_stats",
        type_="unique",
    )
    op.drop_column("player_match_stats", "rating")
    op.drop_column("player_match_stats", "red_cards")
    op.drop_column("player_match_stats", "yellow_cards")
    op.drop_column("player_match_stats", "fouls_committed")
    op.drop_column("player_match_stats", "duels_won")
    op.drop_column("player_match_stats", "pass_accuracy")
    op.drop_column("player_match_stats", "passes")
    op.drop_column("player_match_stats", "shots_on_target")
