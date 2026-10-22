from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel
from sqlalchemy import DateTime, Index, Integer, String, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .telemetry import TripId


class UTCDateTime(TypeDecorator):
    """
    A DateTime type that enforces timezone-aware UTC datetimes.

    In SQLite (used for testing), datetime values lose tzinfo upon storage;
    this TypeDecorator ensures retrieved datetimes are consistently aware UTC.
    In PostgreSQL, it maps directly to TIMESTAMP WITH TIME ZONE.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None:
            if not isinstance(value, datetime):
                raise TypeError(f"Expected datetime object, got {type(value).__name__}")
            if value.tzinfo is None:
                raise ValueError("Expected timezone-aware datetime")
            return value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value


class TripStatus(str, Enum):
    """
    Explicit lifecycle states for a Safety Mode trip session.

    Operational Semantics:
      - INITIALIZED: Trip session initialized; awaiting first telemetry frame.
      - ACTIVE: Live transit session actively streaming telemetry.
      - COMPLETED_NORMAL: Journey explicitly completed; verified normal risk across all windows.
      - COMPLETED_ANOMALOUS: Journey concluded, but flagged with evidenced anomaly or risk escalation.
      - COMPLETED_UNVERIFIED: Journey concluded; completion pending risk inference verification.
      - COMPLETION_PENDING: Semantic alias/synonym for unverified completion.
      - ABORTED_CRISIS: Aborted due to SOS activation or safety policy escalation.
      - EXPIRED_INACTIVE: Terminated due to inactivity timeout (>30 min silence).
    """

    INITIALIZED = "INITIALIZED"
    ACTIVE = "ACTIVE"
    COMPLETED_NORMAL = "COMPLETED_NORMAL"
    COMPLETED_ANOMALOUS = "COMPLETED_ANOMALOUS"
    COMPLETED_UNVERIFIED = "COMPLETED_UNVERIFIED"
    COMPLETION_PENDING = "COMPLETION_PENDING"
    ABORTED_CRISIS = "ABORTED_CRISIS"
    EXPIRED_INACTIVE = "EXPIRED_INACTIVE"


TERMINAL_TRIP_STATUSES: frozenset[TripStatus] = frozenset(
    {
        TripStatus.COMPLETED_NORMAL,
        TripStatus.COMPLETED_ANOMALOUS,
        TripStatus.COMPLETED_UNVERIFIED,
        TripStatus.COMPLETION_PENDING,
        TripStatus.ABORTED_CRISIS,
        TripStatus.EXPIRED_INACTIVE,
    }
)

VALID_TRIP_TRANSITIONS: dict[TripStatus, set[TripStatus]] = {
    TripStatus.INITIALIZED: {
        TripStatus.ACTIVE,
        TripStatus.ABORTED_CRISIS,
        TripStatus.EXPIRED_INACTIVE,
        TripStatus.COMPLETED_ANOMALOUS,
        TripStatus.COMPLETED_UNVERIFIED,
        TripStatus.COMPLETION_PENDING,
    },
    TripStatus.ACTIVE: {
        TripStatus.COMPLETED_NORMAL,
        TripStatus.COMPLETED_ANOMALOUS,
        TripStatus.COMPLETED_UNVERIFIED,
        TripStatus.COMPLETION_PENDING,
        TripStatus.ABORTED_CRISIS,
        TripStatus.EXPIRED_INACTIVE,
    },
    TripStatus.COMPLETED_NORMAL: set(),
    TripStatus.COMPLETED_ANOMALOUS: set(),
    TripStatus.COMPLETED_UNVERIFIED: set(),
    TripStatus.COMPLETION_PENDING: set(),
    TripStatus.ABORTED_CRISIS: set(),
    TripStatus.EXPIRED_INACTIVE: set(),
}


class Trip(Base):
    """
    Persistent representation of a Safety Mode trip.

    Associates each trip session with an authenticated, pseudonymous
    user identity (HMAC-SHA256 user_id) rather than raw device identifiers.
    """

    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    trip_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    user_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TripStatus.INITIALIZED.value,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_trips_user_status_started", "user_id", "status", "started_at"),
    )


# -------------------------------------------------------------------
# Pydantic Schemas for Trip Lifecycle API
# -------------------------------------------------------------------


class StartTripRequest(BaseModel):
    """Request payload to initialize a Safety Mode trip."""

    trip_id: TripId
    started_at: datetime | None = None


class CompleteTripRequest(BaseModel):
    """Request payload to finalize a Safety Mode trip."""

    trip_id: TripId
    ended_at: datetime | None = None
    crisis: bool = False
    anomalous: bool = False
    has_anomaly: bool = False


class TripResponse(BaseModel):
    """Documented response contract for trip lifecycle operations."""

    status: str = "accepted"
    trip_id: str
    trip_status: str
    started_at: datetime
    ended_at: datetime | None = None
