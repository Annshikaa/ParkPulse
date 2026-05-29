from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer,
    String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    bookings: Mapped[list[Booking]] = relationship("Booking", back_populates="user")
    vehicles: Mapped[list[Vehicle]] = relationship("Vehicle", back_populates="user")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    license_plate: Mapped[str] = mapped_column(String(20), nullable=False)
    make_model: Mapped[str | None] = mapped_column(String(100))
    color: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped[User] = relationship("User", back_populates="vehicles")
    bookings: Mapped[list[Booking]] = relationship("Booking", back_populates="vehicle")


class Camera(Base):
    """Physical CCTV / IP camera connected to the system."""
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    rtsp_url: Mapped[str] = mapped_column(String(500), nullable=False)
    # online | offline | error
    status: Mapped[str] = mapped_column(String(20), default="offline")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    last_seen: Mapped[datetime | None] = mapped_column(DateTime)

    slots: Mapped[list[Slot]] = relationship("Slot", back_populates="camera")
    alerts: Mapped[list[Alert]] = relationship("Alert", back_populates="camera")


class Slot(Base):
    __tablename__ = "slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slot_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    # nullable so existing slots without a camera still work
    camera_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cameras.id"), nullable=True)
    polygon_json: Mapped[str] = mapped_column(Text, nullable=False)
    slot_type: Mapped[str] = mapped_column(String(20), default="regular")
    hourly_rate: Mapped[float] = mapped_column(Float, default=50.0)
    # active | inactive
    status: Mapped[str] = mapped_column(String(20), default="active")

    camera: Mapped[Camera | None] = relationship("Camera", back_populates="slots")
    bookings: Mapped[list[Booking]] = relationship("Booking", back_populates="slot")

    @property
    def polygon(self) -> list:
        return json.loads(self.polygon_json)


class Alert(Base):
    """System alerts: camera offline, detection failure, unauthorized parking, etc."""
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    camera_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cameras.id"), nullable=True)
    # camera_offline | detection_failure | unauthorized_parking | system_error
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # info | warning | critical
    severity: Mapped[str] = mapped_column(String(20), default="info")
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    camera: Mapped[Camera | None] = relationship("Camera", back_populates="alerts")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    vehicle_id: Mapped[int] = mapped_column(Integer, ForeignKey("vehicles.id"), nullable=False)
    slot_id: Mapped[int] = mapped_column(Integer, ForeignKey("slots.id"), nullable=False)
    booked_from: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    booked_until: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending_payment")
    estimated_amount: Mapped[float] = mapped_column(Float, default=0.0)
    final_amount: Mapped[float | None] = mapped_column(Float)
    actual_entry_time: Mapped[datetime | None] = mapped_column(DateTime)
    actual_exit_time: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship("User", back_populates="bookings")
    vehicle: Mapped[Vehicle] = relationship("Vehicle", back_populates="bookings")
    slot: Mapped[Slot] = relationship("Slot", back_populates="bookings")
    payment: Mapped[Payment | None] = relationship("Payment", back_populates="booking", uselist=False)
    events: Mapped[list[CVEvent]] = relationship("CVEvent", back_populates="booking")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    booking_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookings.id"), nullable=False)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(100))
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(100))
    razorpay_signature: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR")
    status: Mapped[str] = mapped_column(String(20), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    booking: Mapped[Booking] = relationship("Booking", back_populates="payment")


class CVEvent(Base):
    __tablename__ = "cv_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slot_id: Mapped[int] = mapped_column(Integer, ForeignKey("slots.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(10), nullable=False)
    track_id: Mapped[int] = mapped_column(Integer, default=-1)
    dwell_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    booking_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("bookings.id"), nullable=True)

    booking: Mapped[Booking | None] = relationship("Booking", back_populates="events")


class OccupancySnapshot(Base):
    __tablename__ = "occupancy_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    occupied_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    occupancy_rate: Mapped[float] = mapped_column(Float, nullable=False)
    backend: Mapped[str] = mapped_column(String(20), default="pytorch")
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    camera_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cameras.id"), nullable=True)
