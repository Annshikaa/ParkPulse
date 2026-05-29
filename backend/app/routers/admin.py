"""Admin management endpoints — TIER 2."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.db.models import Booking, User
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit
    total = db.query(func.count(User.id)).scalar()
    users = db.query(User).offset(offset).limit(limit).all()
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
    }


@router.get("/bookings")
def list_all_bookings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Booking)
    if status:
        q = q.filter(Booking.status == status)
    total = q.count()
    bookings = q.order_by(Booking.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": b.id,
                "user_email": b.user.email if b.user else None,
                "slot_number": b.slot.slot_number if b.slot else None,
                "status": b.status,
                "estimated_amount": b.estimated_amount,
                "final_amount": b.final_amount,
                "booked_from": b.booked_from.isoformat(),
                "booked_until": b.booked_until.isoformat(),
                "created_at": b.created_at.isoformat(),
            }
            for b in bookings
        ],
    }


@router.get("/revenue/summary")
def revenue_summary(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    def _sum(since: datetime) -> float:
        return (
            db.query(func.sum(Booking.final_amount))
            .filter(Booking.status == "completed", Booking.updated_at >= since)
            .scalar()
            or 0.0
        )

    return {
        "today": round(_sum(now.replace(hour=0, minute=0, second=0, microsecond=0)), 2),
        "week": round(_sum(now - timedelta(days=7)), 2),
        "month": round(_sum(now - timedelta(days=30)), 2),
    }
