from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth import SECRET_KEY, get_current_user_id
from ..database import get_db
from ..models.telemetry import TelemetryPayload
from ..models.telemetry_record import TelemetryRecord
from ..models.trip import (
    TERMINAL_TRIP_STATUSES,
    CompleteTripRequest,
    StartTripRequest,
    TripStatus,
)
from ..repositories.trip_repository import (
    TripLifecycleError,
    TripOwnershipError,
    TripRepository,
)
from ..services.telemetry_adapter import pseudonymize_identifier

router = APIRouter(prefix="/api/v1", tags=["telemetry"])


@router.post("/telemetry")
def receive_telemetry(
    payload: TelemetryPayload,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    if payload.device_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device identity does not match authenticated identity",
        )

    try:
        if payload.trip_id is not None:
            repo = TripRepository(db)
            trip = repo.get_trip(payload.trip_id)
            if trip is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Trip '{payload.trip_id}' not found",
                )

            pseudonymous_user_id = pseudonymize_identifier(current_user_id, SECRET_KEY)
            if trip.user_id != pseudonymous_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Trip does not belong to authenticated user",
                )

            if trip.status in [s.value for s in TERMINAL_TRIP_STATUSES]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Trip '{payload.trip_id}' is finalized ({trip.status}) "
                        "and cannot accept new telemetry"
                    ),
                )

            if trip.status == TripStatus.INITIALIZED.value:
                repo.update_trip_status(
                    trip_id=payload.trip_id,
                    user_id=pseudonymous_user_id,
                    new_status=TripStatus.ACTIVE,
                    commit=False,
                )

        record = TelemetryRecord(
            version=payload.version,
            device_id=payload.device_id,
            trip_id=payload.trip_id,
            timestamp=payload.timestamp,
            latitude=payload.location.latitude,
            longitude=payload.location.longitude,
            altitude_meters=payload.location.altitude_meters,
            accuracy_meters=payload.location.accuracy_meters,
            speed_mps=payload.speed_mps,
            bearing_degrees=payload.bearing_degrees,
            accelerometer_x=payload.accelerometer.x,
            accelerometer_y=payload.accelerometer.y,
            accelerometer_z=payload.accelerometer.z,
            gyroscope_x=(
                payload.gyroscope.x if payload.gyroscope is not None else None
            ),
            gyroscope_y=(
                payload.gyroscope.y if payload.gyroscope is not None else None
            ),
            gyroscope_z=(
                payload.gyroscope.z if payload.gyroscope is not None else None
            ),
            battery_level=payload.battery_level,
            network_status=payload.network_status,
        )

        db.add(record)
        db.commit()
        db.refresh(record)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist telemetry record",
        ) from exc

    return {
        "status": "accepted",
        "message": "Telemetry received successfully",
        "device_id": payload.device_id,
    }


@router.post("/telemetry/trips/start")
def start_trip(
    payload: StartTripRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Initialize a new Safety Mode trip session.

    Derives a stable pseudonymous user identity from the authenticated client identity.
    Enforces idempotency for duplicate requests from the same user.
    """
    pseudonymous_user_id = pseudonymize_identifier(current_user_id, SECRET_KEY)
    started_at = payload.started_at or datetime.now(timezone.utc)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    repo = TripRepository(db)
    try:
        trip = repo.create_trip(
            trip_id=payload.trip_id,
            user_id=pseudonymous_user_id,
            started_at=started_at,
            status=TripStatus.INITIALIZED,
        )
    except TripOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create trip",
        ) from exc

    return {
        "status": "accepted",
        "trip_id": trip.trip_id,
        "trip_status": trip.status,
        "started_at": trip.started_at,
        "ended_at": trip.ended_at,
    }


@router.post("/telemetry/trips/complete")
def complete_trip(
    payload: CompleteTripRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Finalize an active or initialized Safety Mode trip session.

    Enforces ownership, terminal immutability, and explicit completion semantics:
      - ABORTED_CRISIS: If crisis/SOS activation is explicitly flagged.
      - COMPLETED_ANOMALOUS: If genuine anomaly evidence is indicated.
      - COMPLETED_UNVERIFIED: Default for ordinary completion pending verification.
    COMPLETED_NORMAL is NEVER assigned solely because completion was requested.
    COMPLETED_ANOMALOUS is NEVER assigned without actual anomaly evidence.
    """
    pseudonymous_user_id = pseudonymize_identifier(current_user_id, SECRET_KEY)
    repo = TripRepository(db)

    trip = repo.get_trip(payload.trip_id)
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip '{payload.trip_id}' not found",
        )

    if trip.user_id != pseudonymous_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trip does not belong to authenticated user",
        )

    # Explicit completion policy:
    # 1. If crisis is flagged (manual SOS / safety policy escalation), transition to ABORTED_CRISIS.
    # 2. If genuine anomaly evidence is indicated, transition to COMPLETED_ANOMALOUS.
    # 3. Otherwise, mark COMPLETED_UNVERIFIED (completion requested/pending verification).
    # COMPLETED_NORMAL is NEVER fabricated solely because completion was requested.
    if payload.crisis:
        target_status = TripStatus.ABORTED_CRISIS
    elif payload.anomalous or payload.has_anomaly:
        target_status = TripStatus.COMPLETED_ANOMALOUS
    else:
        target_status = TripStatus.COMPLETED_UNVERIFIED

    ended_at = payload.ended_at or datetime.now(timezone.utc)
    if ended_at.tzinfo is None:
        ended_at = ended_at.replace(tzinfo=timezone.utc)

    if trip.status in [s.value for s in TERMINAL_TRIP_STATUSES]:
        if trip.status == target_status.value:
            # Idempotent repeated completion with identical terminal status
            return {
                "status": "accepted",
                "trip_id": trip.trip_id,
                "trip_status": trip.status,
                "started_at": trip.started_at,
                "ended_at": trip.ended_at,
            }
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Trip '{payload.trip_id}' is already finalized in state '{trip.status}' "
                "and cannot be altered"
            ),
        )

    try:
        updated_trip = repo.update_trip_status(
            trip_id=payload.trip_id,
            user_id=pseudonymous_user_id,
            new_status=target_status,
            ended_at=ended_at,
        )
    except TripLifecycleError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except TripOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete trip",
        ) from exc

    return {
        "status": "accepted",
        "trip_id": updated_trip.trip_id,
        "trip_status": updated_trip.status,
        "started_at": updated_trip.started_at,
        "ended_at": updated_trip.ended_at,
    }


@router.get("/telemetry/{device_id}")
def get_telemetry(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    if device_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device identity does not match authenticated identity",
        )

    records = (
        db.query(TelemetryRecord)
        .filter(TelemetryRecord.device_id == device_id)
        .order_by(TelemetryRecord.timestamp.desc())
        .limit(limit)
        .all()
    )

    return {
        "device_id": device_id,
        "count": len(records),
        "records": [
            {
                "id": record.id,
                "version": record.version,
                "trip_id": record.trip_id,
                "timestamp": record.timestamp,
                "latitude": record.latitude,
                "longitude": record.longitude,
                "altitude_meters": record.altitude_meters,
                "accuracy_meters": record.accuracy_meters,
                "speed_mps": record.speed_mps,
                "bearing_degrees": record.bearing_degrees,
                "accelerometer": {
                    "x": record.accelerometer_x,
                    "y": record.accelerometer_y,
                    "z": record.accelerometer_z,
                },
                "gyroscope": {
                    "x": record.gyroscope_x,
                    "y": record.gyroscope_y,
                    "z": record.gyroscope_z,
                },
                "battery_level": record.battery_level,
                "network_status": record.network_status,
            }
            for record in records
        ],
    }
