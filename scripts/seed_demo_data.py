"""Seed the database with demo data for a rich analytics page from day one.

Creates:
- 1 admin user  (admin@parkpulse.io / Admin@123)
- 3 demo users with vehicles
- 7 days of hourly OccupancySnapshots
- 30 completed bookings with realistic durations and amounts
- 2 currently-active bookings
"""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.db.session import create_all_tables, SessionLocal
from backend.app.db.models import (
    Booking, OccupancySnapshot, Slot, User, Vehicle,
)
from backend.app.security import hash_password

SLOTS_PATH = Path("data/parking_slots.json")


def main() -> None:
    create_all_tables()
    db = SessionLocal()
    try:
        _seed(db)
    finally:
        db.close()
    print("Seed complete.")


def _seed(db) -> None:
    # ------------------------------------------------------------------ Slots
    if not db.query(Slot).first():
        with open(SLOTS_PATH) as f:
            slot_data = json.load(f)
        for s in slot_data:
            db.add(Slot(
                id=s["id"],
                slot_number=s["slot_number"],
                polygon_json=json.dumps(s["polygon"]),
                slot_type=s.get("slot_type", "regular"),
                hourly_rate=s.get("hourly_rate", 50.0),
            ))
        db.flush()
        print(f"  Created {len(slot_data)} slots")

    # ------------------------------------------------------------------ Users
    def get_or_create_user(email, pw, name, phone, role="user"):
        u = db.query(User).filter(User.email == email).first()
        if u:
            return u
        u = User(
            email=email,
            hashed_password=hash_password(pw),
            full_name=name,
            phone=phone,
            role=role,
        )
        db.add(u)
        db.flush()
        return u

    admin = get_or_create_user("admin@parkpulse.io", "Admin@123", "Admin User", "9999999999", "admin")
    u1 = get_or_create_user("rahul@demo.com", "Demo@123", "Rahul Sharma", "9876543210")
    u2 = get_or_create_user("priya@demo.com", "Demo@123", "Priya Nair", "9876543211")
    u3 = get_or_create_user("ankit@demo.com", "Demo@123", "Ankit Verma", "9876543212")
    db.flush()
    print("  Created users")

    # ---------------------------------------------------------------- Vehicles
    def get_or_create_vehicle(user_id, plate, make_model, color):
        v = db.query(Vehicle).filter(Vehicle.license_plate == plate).first()
        if v:
            return v
        v = Vehicle(user_id=user_id, license_plate=plate, make_model=make_model, color=color)
        db.add(v)
        db.flush()
        return v

    v1 = get_or_create_vehicle(u1.id, "MH12AB1234", "Maruti Swift", "White")
    v2 = get_or_create_vehicle(u2.id, "KA03XY5678", "Honda City", "Silver")
    v3 = get_or_create_vehicle(u3.id, "DL8CAF9999", "Hyundai Creta", "Black")
    db.flush()

    # ------------------------------------------------- Historical Snapshots
    snap_count = db.query(OccupancySnapshot).count()
    if snap_count < 10:
        now = datetime.now(timezone.utc)
        slots_total = db.query(Slot).count()
        snaps = []
        for days_back in range(7, -1, -1):
            for hour in range(0, 24):
                ts = now - timedelta(days=days_back, hours=(now.hour - hour))
                # Realistic occupancy curve: low at night, peak at 10am and 6pm
                base = 0.1
                if 8 <= hour <= 10:
                    base = 0.7
                elif 10 <= hour <= 14:
                    base = 0.5
                elif 17 <= hour <= 20:
                    base = 0.8
                elif 0 <= hour <= 6:
                    base = 0.05
                rate = min(1.0, max(0.0, base + random.gauss(0, 0.08)))
                occupied = round(rate * slots_total)
                snaps.append(OccupancySnapshot(
                    timestamp=ts,
                    occupied_count=occupied,
                    total_count=slots_total,
                    occupancy_rate=rate,
                    backend="pytorch",
                    fps=random.uniform(18, 25),
                ))
        db.bulk_save_objects(snaps)
        db.flush()
        print(f"  Created {len(snaps)} occupancy snapshots")

    # --------------------------------------------------- Historical Bookings
    existing_bookings = db.query(Booking).count()
    if existing_bookings < 5:
        slots = db.query(Slot).all()
        users_vehicles = [(u1, v1), (u2, v2), (u3, v3)]
        now = datetime.now(timezone.utc)

        for i in range(30):
            user, vehicle = random.choice(users_vehicles)
            slot = random.choice(slots)
            days_back = random.randint(1, 7)
            hour_start = random.randint(7, 19)
            dur_hours = random.choice([1, 1, 1, 2, 2, 3])
            start = now - timedelta(days=days_back, hours=(now.hour - hour_start))
            end = start + timedelta(hours=dur_hours)
            amount = slot.hourly_rate * dur_hours

            b = Booking(
                user_id=user.id,
                vehicle_id=vehicle.id,
                slot_id=slot.id,
                booked_from=start,
                booked_until=end,
                status="completed",
                estimated_amount=amount,
                final_amount=amount,
                actual_entry_time=start + timedelta(minutes=random.randint(0, 10)),
                actual_exit_time=end - timedelta(minutes=random.randint(0, 5)),
                created_at=start - timedelta(hours=1),
                updated_at=end,
            )
            db.add(b)

        db.flush()
        print("  Created 30 historical bookings")

        # 2 active bookings
        for user, vehicle in [(u1, v1), (u2, v2)]:
            slot = random.choice(slots)
            start = now - timedelta(hours=random.randint(1, 2))
            end = now + timedelta(hours=2)
            b = Booking(
                user_id=user.id,
                vehicle_id=vehicle.id,
                slot_id=slot.id,
                booked_from=start,
                booked_until=end,
                status="active",
                estimated_amount=slot.hourly_rate * 3,
                actual_entry_time=start,
                created_at=start - timedelta(minutes=30),
            )
            db.add(b)
        db.flush()
        print("  Created 2 active bookings")

    db.commit()


if __name__ == "__main__":
    main()
