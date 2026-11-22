"""add sos alert dispatch and trip fields

Revision ID: e5f9a12c3b4d
Revises: c4e8a21f7b90
Create Date: 2026-11-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f9a12c3b4d"
down_revision: Union[str, Sequence[str], None] = "c4e8a21f7b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sos_alerts",
        sa.Column("trip_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "sos_alerts",
        sa.Column(
            "notification_status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "sos_alerts",
        sa.Column(
            "recipients_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_index(
        op.f("ix_sos_alerts_trip_id"),
        "sos_alerts",
        ["trip_id"],
        unique=False,
    )
    op.create_index(
        "ix_trips_status_timer_expires_at",
        "trips",
        ["status", "timer_expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_trips_status_timer_expires_at",
        table_name="trips",
    )
    op.drop_index(op.f("ix_sos_alerts_trip_id"), table_name="sos_alerts")
    op.drop_column("sos_alerts", "recipients_count")
    op.drop_column("sos_alerts", "notification_status")
    op.drop_column("sos_alerts", "trip_id")
