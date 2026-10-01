from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models.telemetry import TelemetryPayload
from ..models.telemetry_record import TelemetryRecord

router = APIRouter(prefix="/api/v1", tags=["telemetry"])


@router.post("/telemetry")
async def receive_telemetry(
    payload: TelemetryPayload,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    if payload.device_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Device identity does not match authenticated identity",
        )

    record = TelemetryRecord(
        version=payload.version,
        device_id=payload.device_id,
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
            payload.gyroscope.x
            if payload.gyroscope is not None
            else None
        ),
        gyroscope_y=(
            payload.gyroscope.y
            if payload.gyroscope is not None
            else None
        ),
        gyroscope_z=(
            payload.gyroscope.z
            if payload.gyroscope is not None
            else None
        ),
        battery_level=payload.battery_level,
        network_status=payload.network_status,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "status": "accepted",
        "message": "Telemetry received successfully",
        "device_id": payload.device_id,
    }


@router.get("/telemetry/{device_id}")
async def get_telemetry(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    if device_id != current_user_id:
        raise HTTPException(
            status_code=403,
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