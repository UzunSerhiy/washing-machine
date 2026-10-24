"""simplify winding calibration

Revision ID: 612fe8276691
Revises: 41f11d4560c9
Create Date: 2026-10-04 17:20:44.677165
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "612fe8276691"
down_revision: Union[str, Sequence[str], None] = "41f11d4560c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_winding_calibrations_material_profile_id",
        "winding_calibrations",
        ["material_profile_id"],
    )

    op.drop_column(
        "winding_calibrations",
        "mode_code",
    )
    op.drop_column(
        "winding_calibrations",
        "name",
    )
    op.drop_column(
        "winding_calibrations",
        "is_active",
    )


def downgrade() -> None:
    op.add_column(
        "winding_calibrations",
        sa.Column(
            "is_active",
            sa.BOOLEAN(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.add_column(
        "winding_calibrations",
        sa.Column(
            "name",
            sa.VARCHAR(length=100),
            nullable=False,
            server_default="Winding calibration",
        ),
    )

    op.add_column(
        "winding_calibrations",
        sa.Column(
            "mode_code",
            sa.VARCHAR(length=30),
            nullable=False,
            server_default="winding",
        ),
    )

    op.drop_constraint(
        "uq_winding_calibrations_material_profile_id",
        "winding_calibrations",
        type_="unique",
    )
