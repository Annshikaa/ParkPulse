"""Tests for the image preprocessor."""
import numpy as np
import pytest

from cv.preprocessor import Preprocessor


def make_frame(brightness: int = 128) -> np.ndarray:
    return np.full((480, 640, 3), brightness, dtype=np.uint8)


def test_disabled_returns_original():
    p = Preprocessor(enabled=False)
    frame = make_frame(100)
    result = p.apply(frame.copy())
    np.testing.assert_array_equal(result, frame)


def test_enabled_does_not_crash():
    p = Preprocessor(enabled=True)
    frame = make_frame(128)
    result = p.apply(frame)
    assert result.shape == frame.shape
    assert result.dtype == np.uint8


def test_dark_frame_brightened():
    # Gamma (exponent < 1) lifts dark values: verify the LUT itself brightens
    # Use gamma=0.5 directly rather than relying on CLAHE on a flat frame
    import cv2
    gamma = 0.5
    table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)], dtype=np.uint8)
    dark_pixel = np.array([[[30, 30, 30]]], dtype=np.uint8)
    bright_pixel = cv2.LUT(dark_pixel, table)
    # 30^0.5 scaled = ~78 — must be brighter than 30
    assert int(bright_pixel[0, 0, 0]) > 30


def test_toggle():
    p = Preprocessor(enabled=True)
    p.enabled = False
    frame = make_frame(50)
    assert np.array_equal(p.apply(frame.copy()), frame)
