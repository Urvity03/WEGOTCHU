"""Repository operations for explicit trip lifecycle management."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ai.route_deviation.loader import Trajectory
from ..models.telemetry_record import TelemetryRecord
from ..models.trip import (
    TERMINAL_TRIP_STATUSES,
    VALID_TRIP_TRANSITIONS,
    Trip,
    TripStatus,
)
from ..services.telemetry_adapter import records_to_candidate_trajectory


class TripRepositoryError(Exception):
    """Base exception for trip repository operations."""


class TripNotFoundError(TripRepositoryError):
    """Raised when a requested trip does not exist."""


class TripOwnershipError(TripRepositoryError):
    """Raised when cross-user trip access or creation collision occurs."""


class TripLifecycleError(TripRepositoryError):
    """Raised when an invalid state transition or terminal-state mutation is attempted."""


class TripRepository:
    """
    Data-access operations for persistent Trip models.

    Enforces:
      - Valid lifecycle states and allowed transitions.
      - Terminal-state immutability (terminal trips cannot reopen).
      - Authenticated user isolation (cross-user access rejected).
      - Idempotent creation for identical trip_id and user_id.
      - Strict UTC normalization for all datetime values.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_trip(
        self,
        trip_id: str,
        user_id: str,
        started_at: datetime,
        status: TripStatus = TripStatus.INITIALIZED,
    ) -> Trip:
        """
        Create a new persistent Trip record or return existing if idempotent.

        Parameters:
            trip_id: Unique client-generated or server-anchored trip session ID.
            user_id: Authenticated pseudonymous user identity (HMAC-SHA256).
                     Raw device identifiers must not be passed here.
            started_at: Timezone-aware starting timestamp.
            status: Initial lifecycle status (defaults to INITIALIZED).

        Returns:
            The created or idempotently matched Trip instance.

        Raises:
            ValueError: If trip_id or user_id is empty/whitespace, or started_at is naive.
            TripOwnershipError: If trip_id already exists belonging to another user.
        """
        if not isinstance(trip_id, str) or not trip_id.strip():
            raise ValueError("trip_id must be a non-empty string")
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        if not isinstance(started_at, datetime):
            raise TypeError("started_at must be a datetime instance")
        if started_at.tzinfo is None:
            raise ValueError("started_at must be a timezone-aware datetime")

        clean_trip_id = trip_id.strip()
        clean_user_id = user_id.strip()
        utc_started_at = started_at.astimezone(timezone.utc)

        if isinstance(status, str):
            status = TripStatus(status)

        existing = self.db.query(Trip).filter(Trip.trip_id == clean_trip_id).first()
        if existing is not None:
            if existing.user_id != clean_user_id:
                raise TripOwnershipError(
                    f"Trip '{clean_trip_id}' already exists and belongs to a different user."
                )
            # Idempotent repeated request from same authenticated user
            return existing

        now_utc = datetime.now(timezone.utc)
        trip = Trip(
            trip_id=clean_trip_id,
            user_id=clean_user_id,
            status=status.value,
            started_at=utc_started_at,
            created_at=now_utc,
            updated_at=now_utc,
        )

        self.db.add(trip)
        self.db.commit()
        self.db.refresh(trip)
        return trip

    def get_trip(
        self,
        trip_id: str,
        user_id: str | None = None,
    ) -> Trip | None:
        """
        Retrieve a trip by its unique identifier.

        If user_id is supplied, ownership is validated. If the trip belongs
        to a different user, TripOwnershipError is raised.
        """
        if not isinstance(trip_id, str) or not trip_id.strip():
            raise ValueError("trip_id must be a non-empty string")

        clean_trip_id = trip_id.strip()
        trip = self.db.query(Trip).filter(Trip.trip_id == clean_trip_id).first()

        if trip is None:
            return None

        if user_id is not None:
            clean_user_id = user_id.strip()
            if trip.user_id != clean_user_id:
                raise TripOwnershipError(
                    f"Access denied: Trip '{clean_trip_id}' does not belong to user '{clean_user_id}'."
                )

        return trip

    def update_trip_status(
        self,
        trip_id: str,
        user_id: str,
        new_status: TripStatus | str,
        ended_at: datetime | None = None,
        commit: bool = True,
    ) -> Trip:
        """
        Transition a trip to a new lifecycle state.

        Enforces:
          - Valid transition per VALID_TRIP_TRANSITIONS.
          - Terminal-state immutability (cannot leave a terminal state).
          - Strict user ownership validation.
          - Proper ended_at recording upon terminal transition.

        Set commit=False to include this update in a caller-managed transaction.
        """
        trip = self.get_trip(trip_id=trip_id, user_id=user_id)
        if trip is None:
            raise TripNotFoundError(f"Trip '{trip_id}' not found.")

        if isinstance(new_status, str):
            new_status = TripStatus(new_status)

        current_status = TripStatus(trip.status)

        # Terminal state immutability
        if current_status in TERMINAL_TRIP_STATUSES:
            if new_status == current_status:
                return trip
            raise TripLifecycleError(
                f"Cannot transition trip '{trip_id}' from terminal state "
                f"'{current_status.value}' to '{new_status.value}'. Terminal states are immutable."
            )

        # Transition legality check
        allowed_targets = VALID_TRIP_TRANSITIONS.get(current_status, set())
        if new_status != current_status and new_status not in allowed_targets:
            raise TripLifecycleError(
                f"Invalid lifecycle transition for trip '{trip_id}': "
                f"cannot transition from '{current_status.value}' to '{new_status.value}'."
            )

        # Process ended_at for terminal states
        if new_status in TERMINAL_TRIP_STATUSES:
            if ended_at is not None:
                if ended_at.tzinfo is None:
                    raise ValueError("ended_at must be a timezone-aware datetime")
                trip.ended_at = ended_at.astimezone(timezone.utc)
            elif trip.ended_at is None:
                trip.ended_at = datetime.now(timezone.utc)
        elif ended_at is not None:
            if ended_at.tzinfo is None:
                raise ValueError("ended_at must be a timezone-aware datetime")
            trip.ended_at = ended_at.astimezone(timezone.utc)

        trip.status = new_status.value
        trip.updated_at = datetime.now(timezone.utc)

        if commit:
            self.db.commit()
            self.db.refresh(trip)
        return trip

    def get_eligible_reference_trips(
        self,
        user_id: str,
        before_timestamp: datetime,
        exclude_trip_id: str | None = None,
    ) -> list[Trip]:
        """
        Retrieve eligible historical reference trips for a user.

        Rules:
          1. Pseudonymous User Isolation: Only trips matching user_id.
          2. Explicit Normal Completion: Status must equal COMPLETED_NORMAL.
             (Pending, unverified, anomalous, aborted, and expired trips are strictly excluded).
          3. Strict Temporal Precedence: the trip started and ended before
             before_timestamp.
          4. Deterministic Ordering: started_at ASC, trip_id ASC.
        """
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        if not isinstance(before_timestamp, datetime):
            raise TypeError("before_timestamp must be a datetime instance")
        if before_timestamp.tzinfo is None:
            raise ValueError("before_timestamp must be a timezone-aware datetime")

        utc_before = before_timestamp.astimezone(timezone.utc)
        clean_user_id = user_id.strip()

        query = self.db.query(Trip).filter(
            Trip.user_id == clean_user_id,
            Trip.status == TripStatus.COMPLETED_NORMAL.value,
            Trip.started_at < utc_before,
            Trip.ended_at < utc_before,
        )
        if exclude_trip_id is not None:
            query = query.filter(Trip.trip_id != exclude_trip_id)
        return query.order_by(Trip.started_at.asc(), Trip.trip_id.asc()).all()

    def get_eligible_historical_trajectories(
        self,
        user_id: str,
        before_timestamp: datetime,
        exclude_trip_id: str | None = None,
    ) -> list[Trajectory]:
        """
        Retrieve eligible historical reference trajectories for a user.

        Guarantees:
          1. Same Pseudonymous User: Only trips belonging to user_id.
          2. Explicit Normal Completion: Only trips in COMPLETED_NORMAL status.
             Trips in INITIALIZED, ACTIVE, COMPLETED_UNVERIFIED,
             COMPLETION_PENDING, COMPLETED_ANOMALOUS, ABORTED_CRISIS,
             or EXPIRED_INACTIVE are strictly excluded.
          3. Strict Temporal Precedence: Trip started_at and ended_at both
             precede before_timestamp.
          4. Valid Trajectory: Each trip's telemetry observations are converted
             via records_to_candidate_trajectory (>= 2 valid points required).
        """
        eligible_trips = self.get_eligible_reference_trips(
            user_id=user_id,
            before_timestamp=before_timestamp,
            exclude_trip_id=exclude_trip_id,
        )
        trajectories: list[Trajectory] = []
        for trip in eligible_trips:
            records = (
                self.db.query(TelemetryRecord)
                .filter(TelemetryRecord.trip_id == trip.trip_id)
                .order_by(TelemetryRecord.timestamp.asc(), TelemetryRecord.id.asc())
                .all()
            )
            normalized_records = [
                {
                    "timestamp": (
                        record.timestamp.replace(tzinfo=timezone.utc)
                        if record.timestamp is not None
                        and record.timestamp.tzinfo is None
                        else record.timestamp
                    ),
                    "latitude": record.latitude,
                    "longitude": record.longitude,
                }
                for record in records
            ]

            traj = records_to_candidate_trajectory(
                records=normalized_records,
                user_id=trip.user_id,
                trajectory_id=trip.trip_id,
            )
            if traj is not None:
                trajectories.append(traj)
        return trajectories

    def get_trip_telemetry_records(self, trip_id: str) -> list[dict[str, object]]:
        """Return one trip's persisted telemetry in deterministic chronological order."""
        records = (
            self.db.query(TelemetryRecord)
            .filter(TelemetryRecord.trip_id == trip_id)
            .order_by(TelemetryRecord.timestamp.asc(), TelemetryRecord.id.asc())
            .all()
        )
        return [
            {
                "device_id": record.device_id,
                "timestamp": (
                    record.timestamp.replace(tzinfo=timezone.utc)
                    if record.timestamp.tzinfo is None
                    else record.timestamp
                ),
                "latitude": record.latitude,
                "longitude": record.longitude,
                "speed_mps": record.speed_mps,
                "accelerometer_x": record.accelerometer_x,
                "accelerometer_y": record.accelerometer_y,
                "accelerometer_z": record.accelerometer_z,
                "gyroscope_x": record.gyroscope_x,
                "gyroscope_y": record.gyroscope_y,
                "gyroscope_z": record.gyroscope_z,
            }
            for record in records
        ]
