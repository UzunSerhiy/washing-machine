"""Add optional water start calibration point.

Revision ID: a83f1b09d627
Revises: 612fe8276691
"""
from alembic import op
import sqlalchemy as sa

revision = "a83f1b09d627"
down_revision = "612fe8276691"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("machine_calibrations", sa.Column("water_start_turns", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("machine_calibrations", "water_start_turns")
