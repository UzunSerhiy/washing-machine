"""remove material start turns from winding calibrations

Revision ID: 314630fb4f4d
Revises: b75b16cd7b3c
Create Date: 2026-09-27 21:13:33.558940

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "314630fb4f4d"
down_revision: Union[str, Sequence[str], None] = "b75b16cd7b3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column(
        "winding_calibrations",
        "material_start_turns",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "winding_calibrations",
        sa.Column(
            "material_start_turns",
            sa.Float(),
            nullable=True,
        ),
    )
