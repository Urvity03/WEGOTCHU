"""make gyroscope fields nullable

Revision ID: 389490fc8efc
Revises: 0d9f238a438b
Create Date: 2026-09-30 12:05:58.468464

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "389490fc8efc"
down_revision: Union[str, Sequence[str], None] = "0d9f238a438b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make gyroscope fields nullable."""
    op.alter_column(
        "telemetry_records",
        "gyroscope_x",
        existing_type=sa.Float(),
        nullable=True,
    )

    op.alter_column(
        "telemetry_records",
        "gyroscope_y",
        existing_type=sa.Float(),
        nullable=True,
    )

    op.alter_column(
        "telemetry_records",
        "gyroscope_z",
        existing_type=sa.Float(),
        nullable=True,
    )


def downgrade() -> None:
    """Restore gyroscope fields as non-nullable."""
    op.alter_column(
        "telemetry_records",
        "gyroscope_x",
        existing_type=sa.Float(),
        nullable=False,
    )

    op.alter_column(
        "telemetry_records",
        "gyroscope_y",
        existing_type=sa.Float(),
        nullable=False,
    )

    op.alter_column(
        "telemetry_records",
        "gyroscope_z",
        existing_type=sa.Float(),
        nullable=False,
    )
