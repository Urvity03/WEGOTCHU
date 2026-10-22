"""create trips table and link telemetry

Revision ID: b11a8c8f4cc6
Revises: 389490fc8efc
Create Date: 2026-10-20 12:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b11a8c8f4cc6"
down_revision: Union[str, Sequence[str], None] = "389490fc8efc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create trips table and add nullable trip_id to telemetry_records."""
    op.create_table(
        "trips",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trip_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_id"),
    )
    op.create_index(
        op.f("ix_trips_user_id"),
        "trips",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_trips_status"),
        "trips",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_trips_user_status_started",
        "trips",
        ["user_id", "status", "started_at"],
        unique=False,
    )

    op.add_column(
        "telemetry_records",
        sa.Column(
            "trip_id",
            sa.String(length=64),
            sa.ForeignKey("trips.trip_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_telemetry_records_trip_id"),
        "telemetry_records",
        ["trip_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop trip_id from telemetry_records and remove trips table."""
    op.drop_index(
        op.f("ix_telemetry_records_trip_id"),
        table_name="telemetry_records",
    )
    op.drop_column("telemetry_records", "trip_id")

    op.drop_index("ix_trips_user_status_started", table_name="trips")
    op.drop_index(op.f("ix_trips_status"), table_name="trips")
    op.drop_index(op.f("ix_trips_user_id"), table_name="trips")
    op.drop_table("trips")
