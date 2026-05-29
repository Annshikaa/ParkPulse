"""Alert management router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_admin, get_db
from backend.app.db.models import Alert, User

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertOut(BaseModel):
    id: int
    camera_id: int | None
    alert_type: str
    message: str
    severity: str
    resolved: bool
    created_at: str

    class Config:
        from_attributes = True


class AlertResolve(BaseModel):
    resolved: bool = True


@router.get("", response_model=list[AlertOut])
def list_alerts(
    resolved: bool | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    q = db.query(Alert).order_by(Alert.created_at.desc())
    if resolved is not None:
        q = q.filter(Alert.resolved == resolved)
    if severity:
        q = q.filter(Alert.severity == severity)
    alerts = q.limit(limit).all()
    return [
        AlertOut(
            id=a.id,
            camera_id=a.camera_id,
            alert_type=a.alert_type,
            message=a.message,
            severity=a.severity,
            resolved=a.resolved,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in alerts
    ]


@router.patch("/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(alert_id: int, body: AlertResolve, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = body.resolved
    db.commit()
    db.refresh(alert)
    return AlertOut(
        id=alert.id,
        camera_id=alert.camera_id,
        alert_type=alert.alert_type,
        message=alert.message,
        severity=alert.severity,
        resolved=alert.resolved,
        created_at=alert.created_at.isoformat() if alert.created_at else "",
    )


@router.delete("/{alert_id}", status_code=204)
def delete_alert(alert_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()
