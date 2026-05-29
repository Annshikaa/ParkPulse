"""Pricing logic isolated for testability.

Separated from booking logic so we can unit-test pricing edge cases
(overnight stays, overstay, sub-hour rounding) independently.
"""
from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from backend.app.db.models import Booking, Slot


def calculate_estimated_amount(
    slot: Slot,
    booked_from: datetime,
    booked_until: datetime,
) -> Decimal:
    """Estimate cost for a booking window. Rounds up to nearest 30 minutes."""
    hours = Decimal(str((booked_until - booked_from).total_seconds() / 3600))
    # Round up to nearest 0.5 hour
    hours = (hours * 2).to_integral_value(rounding=ROUND_HALF_UP) / 2
    rate = Decimal(str(slot.hourly_rate))
    return (hours * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_final_amount(
    booking: Booking,
    actual_exit_time: datetime,
) -> Decimal:
    """Final charge based on actual dwell time.

    Undershoot (exit early): charge for actual time only.
    Overstay (exit late): charge for actual time — no penalty in this version.
    """
    entry = booking.actual_entry_time or booking.booked_from
    hours = Decimal(str((actual_exit_time - entry).total_seconds() / 3600))
    hours = max(hours, Decimal("0.5"))  # minimum 30-minute charge
    hours = (hours * 2).to_integral_value(rounding=ROUND_HALF_UP) / 2

    rate = Decimal(str(booking.slot.hourly_rate))
    return (hours * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
