"""add match stats

Revision ID: a1b2c3d4e5f6
Revises: 25024cdcdc88
Create Date: 2026-01-07 21:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "25024cdcdc88"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_match_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("is_home", sa.Boolean(), nullable=False),
        sa.Column("goals", sa.Integer(), nullable=False),
        sa.Column("possession", sa.Float(), nullable=True),
        sa.Column("shots", sa.Integer(), nullable=True),
        sa.Column("shots_on_target", sa.Integer(), nullable=True),
        sa.Column("passes", sa.Integer(), nullable=True),
        sa.Column("pass_accuracy", sa.Float(), nullable=True),
        sa.Column("corners", sa.Integer(), nullable=True),
        sa.Column("fouls", sa.Integer(), nullable=True),
        sa.Column("yellow_cards", sa.Integer(), nullable=True),
        sa.Column("red_cards", sa.Integer(), nullable=True),
        sa.Column("xg", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_team_match_stats_match_id",
        "team_match_stats",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        "ix_team_match_stats_team_id",
        "team_match_stats",
        ["team_id"],
        unique=False,
    )

    op.create_table(
        "player_match_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=True),
        sa.Column("goals", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("shots", sa.Integer(), nullable=True),
        sa.Column("key_passes", sa.Integer(), nullable=True),
        sa.Column("tackles", sa.Integer(), nullable=True),
        sa.Column("interceptions", sa.Integer(), nullable=True),
        sa.Column("xg", sa.Float(), nullable=True),
        sa.Column("xa", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_player_match_stats_match_id",
        "player_match_stats",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        "ix_player_match_stats_player_id",
        "player_match_stats",
        ["player_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_player_match_stats_player_id", table_name="player_match_stats")
    op.drop_index("ix_player_match_stats_match_id", table_name="player_match_stats")
    op.drop_table("player_match_stats")
    op.drop_index("ix_team_match_stats_team_id", table_name="team_match_stats")
    op.drop_index("ix_team_match_stats_match_id", table_name="team_match_stats")
    op.drop_table("team_match_stats")
