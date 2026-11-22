from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user_id
from ..database import get_db
from ..models.sos import SOSAlertCreate
from ..models.sos_alert import SOSAlert
from ..services.dispatch_service import DispatchService

router = APIRouter(prefix="/api/v1/sos", tags=["sos"])


@router.post("", status_code=201)
def create_sos_alert(
    payload: SOSAlertCreate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    if payload.recipients:
        dispatch_result = DispatchService().dispatch_alert(
            user_id=current_user_id,
            recipients=payload.recipients,
            source="manual",
            latitude=payload.latitude,
            longitude=payload.longitude,
            note=payload.note,
        )
        notification_status = dispatch_result.status
        recipients_count = dispatch_result.recipients_count
    else:
        notification_status = "not_configured"
        recipients_count = 0

    alert = SOSAlert(
        user_id=current_user_id,
        status="received",
        source="manual",
        trip_id=payload.trip_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_meters=payload.accuracy_meters,
        note=payload.note,
        created_at=datetime.now(timezone.utc),
        notification_status=notification_status,
        recipients_count=recipients_count,
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "id": alert.id,
        "status": alert.status,
        "source": alert.source,
        "latitude": alert.latitude,
        "longitude": alert.longitude,
        "accuracy_meters": alert.accuracy_meters,
        "created_at": alert.created_at.isoformat(),
        "notification_status": alert.notification_status,
        "recipients_count": alert.recipients_count,
        "trip_id": alert.trip_id,
    }


@router.get("/{alert_id}")
def get_sos_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    alert = (
        db.query(SOSAlert)
        .filter(
            SOSAlert.id == alert_id,
            SOSAlert.user_id == current_user_id,
        )
        .first()
    )

    from fastapi import HTTPException

    if alert is None:
        raise HTTPException(status_code=404, detail="SOS alert not found")

    return {
        "id": alert.id,
        "status": alert.status,
        "source": alert.source,
        "latitude": alert.latitude,
        "longitude": alert.longitude,
        "accuracy_meters": alert.accuracy_meters,
        "created_at": alert.created_at.isoformat(),
        "notification_status": alert.notification_status,
        "recipients_count": alert.recipients_count,
        "trip_id": alert.trip_id,
    }
