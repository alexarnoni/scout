"""round_number nullable

Revision ID: e1f2a3b4c5d6
Revises: 209171472d94
Create Date: 2026-03-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e1f2a3b4c5d6'
down_revision = '209171472d94'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("matches", "round_number", nullable=True)


def downgrade() -> None:
    op.alter_column("matches", "round_number", nullable=False)
