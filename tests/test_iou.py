"""Tests for IoU geometry helpers in SlotManager."""
import pytest
from shapely.geometry import Polygon, box as shapely_box

from cv.slot_manager import SlotManager


def iou(a, b):
    return SlotManager._compute_iou(a, b)


def test_identical_boxes():
    a = shapely_box(0, 0, 10, 10)
    assert iou(a, a) == pytest.approx(1.0)


def test_no_overlap():
    a = shapely_box(0, 0, 5, 5)
    b = shapely_box(10, 10, 20, 20)
    assert iou(a, b) == pytest.approx(0.0)


def test_partial_overlap():
    a = shapely_box(0, 0, 10, 10)
    b = shapely_box(5, 0, 15, 10)
    # intersection = 5*10 = 50, union = 10*10 + 10*10 - 50 = 150
    assert iou(a, b) == pytest.approx(50 / 150)


def test_contained():
    outer = shapely_box(0, 0, 10, 10)
    inner = shapely_box(2, 2, 8, 8)
    # intersection = 36, union = 100
    assert iou(outer, inner) == pytest.approx(36 / 100)


def test_vehicle_polygon_shape():
    slot = Polygon([[50, 200], [150, 200], [150, 320], [50, 320]])
    vehicle = shapely_box(60, 210, 140, 310)
    result = iou(vehicle, slot)
    assert result > 0.5  # most of vehicle is inside slot
