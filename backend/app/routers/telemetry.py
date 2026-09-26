from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.telemetry import TelemetryPayload
from ..models.telemetry_record import TelemetryRecord

router = APIRouter(prefix="/api/v1", tags=["telemetry"])


@router.post("/telemetry")
async def receive_telemetry(
    payload: TelemetryPayload,
    db: Session = Depends(get_db),
):
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
        gyroscope_x=payload.gyroscope.x,
        gyroscope_y=payload.gyroscope.y,
        gyroscope_z=payload.gyroscope.z,
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
