import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ai.genai import (
    BriefingAudience,
    GenAIBriefingRequest,
    GenAIBriefingService,
)
from ai.risk_engine.engine import RiskEngine
from ai.risk_engine.models import RiskAssessment, RiskLevel
from ..auth import SECRET_KEY, get_current_user_id
from ..database import get_db
from ..models.telemetry import TelemetryPayload
from ..models.telemetry_record import TelemetryRecord
from ..models.trip import (
    TERMINAL_TRIP_STATUSES,
    CompleteTripRequest,
    StartTripRequest,
    Trip,
    TripBriefingRequest,
    TripStatus,
)
from ..repositories.trip_repository import (
    TripLifecycleError,
    TripOwnershipError,
    TripRepository,
)
from ..services.risk_service import RiskService
from ..services.telemetry_adapter import pseudonymize_identifier

router = APIRouter(prefix="/api/v1", tags=["telemetry"])
logger = logging.getLogger(__name__)

# Multi-Window Evidence & Coverage Policy Constants (Provisional Baseline)
MIN_VERIFIED_TRIP_DURATION_SECONDS: float = 30.0
MIN_VERIFIED_TELEMETRY_RECORDS: int = 10
MAX_PERMITTED_OBSERVATION_GAP_SECONDS: float = 15.0


def check_trip_coverage_eligibility(
    trip: Trip,
    records: list[dict[str, object]],
    assessment: RiskAssessment,
    min_duration_seconds: float = MIN_VERIFIED_TRIP_DURATION_SECONDS,
    min_records: int = MIN_VERIFIED_TELEMETRY_RECORDS,
    max_gap_seconds: float = MAX_PERMITTED_OBSERVATION_GAP_SECONDS,
) -> bool:
    """
    Evaluate whether an active trip satisfies multi-window evidence coverage
    required to transition to COMPLETED_NORMAL.

    Guarantees:
      - Only active trips can qualify (INITIALIZED trips cannot).
      - Rejects trips where risk assessment is not NORMAL, signals is non-empty,
        or confidence is below 0.70.
      - Both route and motion detector statuses must equal 'SUCCESS'.
      - Must contain >= min_records valid observation records with finite GPS and IMU.
      - Deduplicates timestamps and verifies >= min_records distinct observation times.
      - Total temporal span across observations must be >= min_duration_seconds.
      - Rejects clustered observations: every consecutive observation interval must
        be <= max_gap_seconds (preventing unmonitored telemetry blackouts).
    """
    if trip.status != TripStatus.ACTIVE.value:
        return False

    if assessment.risk_level != RiskLevel.NORMAL or assessment.signals:
        return False

    if assessment.confidence < 0.70:
        return False

    if (
        assessment.telemetry_summary.route_status != "SUCCESS"
        or assessment.telemetry_summary.motion_status != "SUCCESS"
    ):
        return False

    if len(records) < min_records:
        return False

    # Extract and validate individual telemetry records
    valid_records: list[dict[str, object]] = []
    for r in records:
        ts = r.get("timestamp")
        if not isinstance(ts, datetime):
            continue

        lat = r.get("latitude")
        lon = r.get("longitude")
        if (
            not isinstance(lat, (int, float))
            or isinstance(lat, bool)
            or not math.isfinite(lat)
            or not (-90.0 <= lat <= 90.0)
        ):
            continue
        if (
            not isinstance(lon, (int, float))
            or isinstance(lon, bool)
            or not math.isfinite(lon)
            or not (-180.0 <= lon <= 180.0)
        ):
            continue

        # Accelerometer axes must be finite numbers
        imu_valid = True
        for axis in ("accelerometer_x", "accelerometer_y", "accelerometer_z"):
            val = r.get(axis)
            if (
                not isinstance(val, (int, float))
                or isinstance(val, bool)
                or not math.isfinite(val)
            ):
                imu_valid = False
                break
        if not imu_valid:
            continue

        valid_records.append(r)

    if len(valid_records) < min_records:
        return False

    # Extract distinct, sorted timestamps (normalized to UTC)
    unique_timestamps = sorted(
        {
            (
                r["timestamp"].replace(tzinfo=timezone.utc)
                if r["timestamp"].tzinfo is None
                else r["timestamp"].astimezone(timezone.utc)
            )
            for r in valid_records
        }
    )

    if len(unique_timestamps) < min_records:
        return False

    total_duration = (unique_timestamps[-1] - unique_timestamps[0]).total_seconds()
    if total_duration < min_duration_seconds:
        return False

    # Enforce maximum permitted gap between consecutive observations
    for i in range(len(unique_timestamps) - 1):
        gap = (unique_timestamps[i + 1] - unique_timestamps[i]).total_seconds()
        if gap > max_gap_seconds:
            return False

    return True


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
      - COMPLETED_ANOMALOUS: If trip-level inference reports supported anomaly signals.
      - COMPLETED_UNVERIFIED: Default for ordinary completion pending verification.
    COMPLETED_NORMAL is NEVER assigned solely because completion was requested.
    Client-provided anomaly flags are compatibility-only and are not evidence.
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

    ended_at = payload.ended_at or datetime.now(timezone.utc)
    if ended_at.tzinfo is None:
        ended_at = ended_at.replace(tzinfo=timezone.utc)

    if trip.status in [s.value for s in TERMINAL_TRIP_STATUSES]:
        if (payload.crisis and trip.status == TripStatus.ABORTED_CRISIS.value) or (
            not payload.crisis
            and trip.status
            in {
                TripStatus.COMPLETED_UNVERIFIED.value,
                TripStatus.COMPLETED_ANOMALOUS.value,
            }
        ):
            # Repeated completion does not rerun inference or change the terminal state.
            return {
                "status": "accepted",
                "trip_id": trip.trip_id,
                "trip_status": trip.status,
                "started_at": trip.started_at,
                "ended_at": trip.ended_at,
                "inference_status": "NOT_RUN",
                "risk_assessment": None,
            }
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Trip '{payload.trip_id}' is already finalized in state '{trip.status}' "
                "and cannot be altered"
            ),
        )

    risk_assessment = None
    if payload.crisis:
        target_status = TripStatus.ABORTED_CRISIS
        inference_status = "SKIPPED_CRISIS"
    else:
        target_status = TripStatus.COMPLETED_UNVERIFIED
        inference_status = "INSUFFICIENT_DATA"
        try:
            records = repo.get_trip_telemetry_records(payload.trip_id)
            if records:
                historical_trajectories = (
                    repo.get_eligible_historical_trajectories(
                        user_id=pseudonymous_user_id,
                        before_timestamp=trip.started_at,
                        exclude_trip_id=trip.trip_id,
                    )
                    if len(records) >= 2
                    else []
                )
                risk_assessment = RiskService(
                    raise_on_detector_error=True
                ).evaluate_telemetry(
                    user_id=pseudonymous_user_id,
                    records=records,
                    trajectory_id=trip.trip_id,
                    historical_trajectories=historical_trajectories,
                )
                inference_status = "COMPLETED"
                if risk_assessment.signals:
                    target_status = TripStatus.COMPLETED_ANOMALOUS
                elif check_trip_coverage_eligibility(trip, records, risk_assessment):
                    target_status = TripStatus.COMPLETED_NORMAL
        except Exception as exc:
            db.rollback()
            inference_status = "FAILED"
            risk_assessment = None
            logger.warning(
                "Trip risk assessment failed; leaving trip unverified (%s)",
                type(exc).__name__,
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
        "inference_status": inference_status,
        "risk_assessment": (
            risk_assessment.to_dict(include_extended_metadata=True)
            if risk_assessment is not None
            else None
        ),
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


@router.post("/telemetry/trips/{trip_id}/briefing")
def get_trip_briefing(
    trip_id: str,
    payload: TripBriefingRequest | None = None,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Generate an authenticated, guardrail-verified GenAI safety briefing for a trip.

    Security & Safety Guarantees:
      - Authenticated user isolation: strictly forbids access to another user's trip (403).
      - Returns 404 if the requested trip does not exist.
      - Non-authoritative GenAI: uses deterministic RiskAssessment as inviolable source of truth.
      - Safe offline fallback: uses deterministic templates without paid API dependencies or credentials.
      - Discloses missing evidence and standard safety disclaimers explicitly.
    """
    pseudonymous_user_id = pseudonymize_identifier(current_user_id, SECRET_KEY)
    repo = TripRepository(db)

    trip = repo.get_trip(trip_id)
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip '{trip_id}' not found",
        )

    if trip.user_id != pseudonymous_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trip does not belong to authenticated user",
        )

    # Fetch persisted records and evaluate authoritative assessment
    records = repo.get_trip_telemetry_records(trip.trip_id)
    if records:
        historical_trajectories = (
            repo.get_eligible_historical_trajectories(
                user_id=pseudonymous_user_id,
                before_timestamp=trip.started_at,
                exclude_trip_id=trip.trip_id,
            )
            if len(records) >= 2
            else []
        )
        assessment = RiskService(raise_on_detector_error=False).evaluate_telemetry(
            user_id=pseudonymous_user_id,
            records=records,
            trajectory_id=trip.trip_id,
            historical_trajectories=historical_trajectories,
        )
    else:
        assessment = RiskEngine().evaluate(user_id=pseudonymous_user_id)

    # Determine available and missing evidence modalities
    available_modalities: list[str] = []
    missing_modalities: list[str] = []

    if assessment.telemetry_summary.motion_status == "SUCCESS":
        available_modalities.append("motion")
    else:
        missing_modalities.append("motion")

    if assessment.telemetry_summary.route_status == "SUCCESS":
        available_modalities.append("route")
    else:
        missing_modalities.append("route")

    missing_modalities.append("acoustic")  # Not yet integrated in v0.1

    audience_val = BriefingAudience.USER
    display_name = "User"
    if payload is not None:
        try:
            audience_val = BriefingAudience(payload.audience)
        except ValueError:
            audience_val = BriefingAudience.USER
        display_name = payload.user_display_name or "User"

    briefing_req = GenAIBriefingRequest(
        risk_level=assessment.risk_level.value,
        confidence=assessment.confidence,
        signals=assessment.signals,
        location_status=assessment.location_status,
        available_modalities=tuple(available_modalities),
        missing_modalities=tuple(missing_modalities),
        motion_state=assessment.telemetry_summary.motion_state,
        corridor_deviation_meters=assessment.telemetry_summary.corridor_deviation_meters,
        speed_mps=assessment.telemetry_summary.speed_mps,
        recommended_action=assessment.recommended_action.value,
        audience=audience_val,
        user_display_name=display_name,
    )

    service = GenAIBriefingService()
    briefing = service.synthesize_briefing(briefing_req)
    return briefing.model_dump()
