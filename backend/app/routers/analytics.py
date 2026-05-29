"""Admin analytics endpoints — TIER 2."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.db.models import Booking, OccupancySnapshot, Slot
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_admin
from backend.app.db.models import User

router = APIRouter(prefix="/analytics", tags=["analytics"])

RangeParam = Literal["1h", "6h", "24h", "7d"]

RANGE_DELTA = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}


def _start_time(range_: str) -> datetime:
    return datetime.now(timezone.utc) - RANGE_DELTA.get(range_, timedelta(hours=24))


@router.get("/occupancy-timeseries")
def occupancy_timeseries(
    range: RangeParam = Query("24h"),
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    since = _start_time(range)
    rows = (
        db.query(OccupancySnapshot)
        .filter(OccupancySnapshot.timestamp >= since)
        .order_by(OccupancySnapshot.timestamp)
        .all()
    )
    return [
        {
            "timestamp": r.timestamp.isoformat(),
            "occupied": r.occupied_count,
            "total": r.total_count,
            "rate": round(r.occupancy_rate * 100, 1),
            "fps": r.fps,
        }
        for r in rows
    ]


@router.get("/revenue")
def revenue(
    range: RangeParam = Query("24h"),
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    since = _start_time(range)
    total = (
        db.query(func.sum(Booking.final_amount))
        .filter(
            Booking.status == "completed",
            Booking.updated_at >= since,
        )
        .scalar()
        or 0.0
    )
    count = (
        db.query(func.count(Booking.id))
        .filter(Booking.status == "completed", Booking.updated_at >= since)
        .scalar()
        or 0
    )
    return {"total_revenue": round(total, 2), "completed_bookings": count, "range": range}


@router.get("/slot-utilization")
def slot_utilization(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    slots = db.query(Slot).all()
    result = []
    for slot in slots:
        completed = (
            db.query(func.count(Booking.id))
            .filter(Booking.slot_id == slot.id, Booking.status == "completed")
            .scalar()
            or 0
        )
        revenue = (
            db.query(func.sum(Booking.final_amount))
            .filter(Booking.slot_id == slot.id, Booking.status == "completed")
            .scalar()
            or 0.0
        )
        result.append({
            "slot_id": slot.id,
            "slot_number": slot.slot_number,
            "slot_type": slot.slot_type,
            "completed_bookings": completed,
            "total_revenue": round(revenue, 2),
        })
    return sorted(result, key=lambda x: x["total_revenue"], reverse=True)


@router.get("/hourly-heatmap")
def hourly_heatmap(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            func.strftime("%H", OccupancySnapshot.timestamp).label("hour"),
            func.avg(OccupancySnapshot.occupancy_rate).label("avg_rate"),
        )
        .group_by("hour")
        .all()
    )
    return [{"hour": int(r.hour), "avg_occupancy_rate": round(r.avg_rate * 100, 1)} for r in rows]


@router.get("/dwell-distribution")
def dwell_distribution(
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    bookings = (
        db.query(Booking)
        .filter(
            Booking.status == "completed",
            Booking.actual_entry_time.isnot(None),
            Booking.actual_exit_time.isnot(None),
        )
        .all()
    )
    buckets = {f"{i}-{i+30}min": 0 for i in range(0, 180, 30)}
    buckets["180+min"] = 0
    for b in bookings:
        mins = (b.actual_exit_time - b.actual_entry_time).total_seconds() / 60
        if mins < 30:
            buckets["0-30min"] += 1
        elif mins < 60:
            buckets["30-60min"] += 1
        elif mins < 90:
            buckets["60-90min"] += 1
        elif mins < 120:
            buckets["90-120min"] += 1
        elif mins < 150:
            buckets["120-150min"] += 1
        elif mins < 180:
            buckets["150-180min"] += 1
        else:
            buckets["180+min"] += 1
    return [{"bucket": k, "count": v} for k, v in buckets.items()]
