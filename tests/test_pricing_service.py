"""Tests for pricing edge cases."""
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from backend.app.services.pricing_service import calculate_estimated_amount, calculate_final_amount


def make_slot(hourly_rate=50.0):
    slot = MagicMock()
    slot.hourly_rate = hourly_rate
    return slot


def dt(h, m=0):
    return datetime(2024, 1, 1, h, m, tzinfo=timezone.utc)


def test_one_hour():
    result = calculate_estimated_amount(make_slot(50.0), dt(10), dt(11))
    assert result == Decimal("50.00")


def test_two_hours():
    result = calculate_estimated_amount(make_slot(50.0), dt(10), dt(12))
    assert result == Decimal("100.00")


def test_rounds_up_to_half_hour():
    # 1h 20min → rounds up to 1.5h
    result = calculate_estimated_amount(make_slot(50.0), dt(10), dt(11, 20))
    assert result == Decimal("75.00")


def test_exact_half_hour():
    result = calculate_estimated_amount(make_slot(50.0), dt(10), dt(10, 30))
    assert result == Decimal("25.00")


def test_minimum_charge_in_final():
    slot = make_slot(50.0)
    booking = MagicMock()
    booking.actual_entry_time = dt(10)
    booking.booked_from = dt(10)
    booking.slot = slot
    # Exit after only 10 minutes → minimum 0.5h charge
    result = calculate_final_amount(booking, dt(10, 10))
    assert result == Decimal("25.00")


def test_final_amount_full_stay():
    slot = make_slot(60.0)
    booking = MagicMock()
    booking.actual_entry_time = dt(9)
    booking.booked_from = dt(9)
    booking.slot = slot
    result = calculate_final_amount(booking, dt(12))
    assert result == Decimal("180.00")
