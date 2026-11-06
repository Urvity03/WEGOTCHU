"""add safety timer fields to trips

Revision ID: c4e8a21f7b90
Revises: 8255d79f0615
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e8a21f7b90"
down_revision: Union[str, Sequence[str], None] = "8255d79f0615"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trips",
        sa.Column("timer_duration_seconds", sa.Integer(), nullable=True),
    )
    op.add_column(
        "trips",
        sa.Column("timer_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("trips", "timer_expires_at")
    op.drop_column("trips", "timer_duration_seconds")
