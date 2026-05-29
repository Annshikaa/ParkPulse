"""Booking CRUD — TIER 2."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models import Booking, Slot, Vehicle
from backend.app.dependencies import get_current_user, get_current_admin
from backend.app.db.models import User
from backend.app.services.pricing_service import calculate_estimated_amount

router = APIRouter(prefix="/bookings", tags=["bookings"])


class CreateBookingRequest(BaseModel):
    slot_id: int
    vehicle_id: int
    booked_from: datetime
    booked_until: datetime


def _serialize_booking(b: Booking) -> dict:
    return {
        "id": b.id,
        "slot_id": b.slot_id,
        "slot_number": b.slot.slot_number if b.slot else None,
        "vehicle_id": b.vehicle_id,
        "license_plate": b.vehicle.license_plate if b.vehicle else None,
        "booked_from": b.booked_from.isoformat(),
        "booked_until": b.booked_until.isoformat(),
        "status": b.status,
        "estimated_amount": b.estimated_amount,
        "final_amount": b.final_amount,
        "actual_entry_time": b.actual_entry_time.isoformat() if b.actual_entry_time else None,
        "actual_exit_time": b.actual_exit_time.isoformat() if b.actual_exit_time else None,
        "created_at": b.created_at.isoformat(),
    }


def _check_overlap(db: Session, slot_id: int, from_: datetime, until: datetime, exclude_id: int | None = None) -> bool:
    q = db.query(Booking).filter(
        Booking.slot_id == slot_id,
        Booking.status.in_(["confirmed", "active", "pending_payment"]),
        Booking.booked_from < until,
        Booking.booked_until > from_,
    )
    if exclude_id:
        q = q.filter(Booking.id != exclude_id)
    return q.first() is not None


@router.post("", status_code=201)
def create_booking(
    body: CreateBookingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    slot = db.get(Slot, body.slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    vehicle = db.get(Vehicle, body.vehicle_id)
    if not vehicle or vehicle.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Vehicle not found or not yours")

    if body.booked_until <= body.booked_from:
        raise HTTPException(status_code=400, detail="booked_until must be after booked_from")

    if _check_overlap(db, body.slot_id, body.booked_from, body.booked_until):
        raise HTTPException(status_code=409, detail="Slot already booked for this time range")

    amount = calculate_estimated_amount(slot, body.booked_from, body.booked_until)

    booking = Booking(
        user_id=current_user.id,
        vehicle_id=body.vehicle_id,
        slot_id=body.slot_id,
        booked_from=body.booked_from,
        booked_until=body.booked_until,
        status="pending_payment",
        estimated_amount=float(amount),
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return _serialize_booking(booking)


@router.get("/my")
def my_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == current_user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    return [_serialize_booking(b) for b in bookings]


@router.get("/availability")
def check_availability(
    slot_id: int = Query(...),
    from_: datetime = Query(..., alias="from"),
    until: datetime = Query(...),
    db: Session = Depends(get_db),
):
    overlap = _check_overlap(db, slot_id, from_, until)
    return {"available": not overlap, "slot_id": slot_id}


@router.get("/{booking_id}")
def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    b = db.get(Booking, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return _serialize_booking(b)


@router.patch("/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    b = db.get(Booking, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    if b.status not in ("pending_payment", "confirmed"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel booking in status: {b.status}")

    b.status = "cancelled"
    db.commit()
    return {"message": "Booking cancelled", "id": booking_id}


@router.patch("/{booking_id}/confirm")
def confirm_booking_mock(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mock payment confirmation for demo/TIER 2 mode (no Razorpay)."""
    b = db.get(Booking, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    if b.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    if b.status != "pending_payment":
        raise HTTPException(status_code=400, detail=f"Cannot confirm booking in status: {b.status}")

    b.status = "confirmed"
    db.commit()
    return {"message": "Booking confirmed (demo mode)", "id": booking_id, "status": "confirmed"}
