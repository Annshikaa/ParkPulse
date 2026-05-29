"""Tests for SlotManager hysteresis and event emission."""
import json
import tempfile
from pathlib import Path

import pytest

from cv.detector import Detection
from cv.slot_manager import SlotManager, SlotEvent


SLOTS_DATA = [
    {"id": 1, "slot_number": "A1", "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]],
     "slot_type": "regular", "hourly_rate": 50.0},
]


@pytest.fixture
def slots_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(SLOTS_DATA, f)
        return Path(f.name)


@pytest.fixture
def manager(slots_file):
    return SlotManager(slots_path=slots_file, enter_frames=3, exit_frames=5)


def make_det(x1=10, y1=10, x2=90, y2=90, track_id=1):
    return Detection(x1=x1, y1=y1, x2=x2, y2=y2, conf=0.9, cls=2, track_id=track_id)


def test_no_event_before_enter_frames(manager):
    det = make_det()
    for _ in range(2):
        events = manager.update([det])
        assert len(events) == 0


def test_enter_event_after_enter_frames(manager):
    det = make_det()
    all_events = []
    for _ in range(3):
        all_events += manager.update([det])
    enters = [e for e in all_events if e.event_type == "enter"]
    assert len(enters) == 1
    assert enters[0].slot_id == 1


def test_no_exit_before_exit_frames(manager):
    det = make_det()
    for _ in range(3):
        manager.update([det])
    # Now remove vehicle — should not exit for < 5 frames
    for _ in range(4):
        events = manager.update([])
        assert not any(e.event_type == "exit" for e in events)


def test_exit_event_after_exit_frames(manager):
    det = make_det()
    for _ in range(3):
        manager.update([det])
    all_events = []
    for _ in range(5):
        all_events += manager.update([])
    exits = [e for e in all_events if e.event_type == "exit"]
    assert len(exits) == 1
    assert exits[0].slot_id == 1


def test_stats_occupied(manager):
    det = make_det()
    for _ in range(3):
        manager.update([det])
    stats = manager.stats()
    assert stats["occupied"] == 1
    assert stats["free"] == 0


def test_stats_free_after_exit(manager):
    det = make_det()
    for _ in range(3):
        manager.update([det])
    for _ in range(5):
        manager.update([])
    stats = manager.stats()
    assert stats["occupied"] == 0
    assert stats["free"] == 1
