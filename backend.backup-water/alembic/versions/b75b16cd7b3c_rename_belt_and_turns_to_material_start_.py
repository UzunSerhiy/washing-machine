"""rename belt and turns to material start turns

Revision ID: b75b16cd7b3c
Revises: 2eccb1b32574
Create Date: 2026-09-27 20:12:32.071342

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b75b16cd7b3c"
down_revision: Union[str, Sequence[str], None] = "2eccb1b32574"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "winding_calibrations",
        "belt_end_turns",
        new_column_name="material_start_turns",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "winding_calibrations",
        "material_start_turns",
        new_column_name="belt_end_turns",
    )
