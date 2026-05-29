"""Razorpay payment integration — TIER 3."""
from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.db.models import Booking, Payment
from backend.app.db.session import get_db
from backend.app.dependencies import get_current_user
from backend.app.db.models import User

router = APIRouter(prefix="/payments", tags=["payments"])


class CreateOrderRequest(BaseModel):
    booking_id: int


class VerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    booking_id: int


@router.post("/create-order")
def create_order(
    body: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not settings.razorpay_key_id:
        raise HTTPException(status_code=503, detail="Razorpay not configured. Use mock payment.")

    booking = db.get(Booking, body.booking_id)
    if not booking or booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "pending_payment":
        raise HTTPException(status_code=400, detail="Booking not in pending_payment state")

    import razorpay

    client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
    amount_paise = int(booking.estimated_amount * 100)
    order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"booking_{booking.id}",
        "notes": {"booking_id": str(booking.id)},
    })

    payment = Payment(
        booking_id=booking.id,
        razorpay_order_id=order["id"],
        amount=booking.estimated_amount,
        currency="INR",
        status="created",
    )
    db.add(payment)
    db.commit()

    return {
        "razorpay_order_id": order["id"],
        "amount": amount_paise,
        "currency": "INR",
        "key_id": settings.razorpay_key_id,
        "booking_id": booking.id,
    }


@router.post("/verify")
def verify_payment(
    body: VerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not settings.razorpay_key_secret:
        raise HTTPException(status_code=503, detail="Razorpay not configured")

    # HMAC-SHA256 signature verification
    expected = hmac.new(
        settings.razorpay_key_secret.encode(),
        f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    booking = db.get(Booking, body.booking_id)
    if not booking or booking.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = "confirmed"

    payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
    if payment:
        payment.razorpay_payment_id = body.razorpay_payment_id
        payment.razorpay_signature = body.razorpay_signature
        payment.status = "paid"

    db.commit()
    return {"message": "Payment verified", "booking_id": booking.id, "status": "confirmed"}


@router.post("/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Async confirmation from Razorpay — verifies webhook signature."""
    body = await request.body()
    sig = request.headers.get("X-Razorpay-Signature", "")

    if settings.razorpay_key_secret:
        expected = hmac.new(
            settings.razorpay_key_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json
    payload = json.loads(body)
    event = payload.get("event", "")

    if event == "payment.captured":
        order_id = payload["payload"]["payment"]["entity"].get("order_id")
        payment = db.query(Payment).filter(Payment.razorpay_order_id == order_id).first()
        if payment and payment.status != "paid":
            payment.status = "paid"
            payment.booking.status = "confirmed"
            db.commit()

    return {"status": "ok"}
