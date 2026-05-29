"""Auto-detect parking slots from a CCTV frame.

Strategy:
1. Run YOLO detections → occupied slot bboxes (car + padding)
2. Edge + contour analysis → candidate empty-space rectangles
3. NMS deduplication → keep non-overlapping slots
4. Sort spatially and label A1, A2 … B1, B2 …
"""
from __future__ import annotations

import cv2
import numpy as np


def _iou(a: tuple, b: tuple) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    aa = (a[2] - a[0]) * (a[3] - a[1])
    ab = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (aa + ab - inter + 1e-6)


def detect_slots(
    frame: np.ndarray,
    detections=None,
    max_slots: int = 80,
) -> list[dict]:
    """Return parking slot dicts detected from *frame*.

    Each dict: id, slot_number, polygon [[x,y]×4], slot_type, hourly_rate.
    *detections* is an optional list of cv.detector.Detection objects from
    the live YOLO pipeline — used as anchor boxes for occupied spots.
    """
    h, w = frame.shape[:2]
    all_boxes: list[tuple[int, int, int, int]] = []

    # ── 1. YOLO car bboxes → occupied slot candidates ──────────────────
    car_boxes: list[tuple[int, int, int, int]] = []
    if detections:
        for det in detections:
            x1, y1, x2, y2 = int(det.x1), int(det.y1), int(det.x2), int(det.y2)
            bw, bh = max(x2 - x1, 1), max(y2 - y1, 1)
            px, py = max(4, int(bw * 0.08)), max(4, int(bh * 0.06))
            box = (max(0, x1 - px), max(0, y1 - py), min(w, x2 + px), min(h, y2 + py))
            car_boxes.append(box)
            all_boxes.append(box)

    # Typical slot dimensions (from cars, or frame-relative defaults)
    if car_boxes:
        avg_w = int(np.mean([b[2] - b[0] for b in car_boxes]))
        avg_h = int(np.mean([b[3] - b[1] for b in car_boxes]))
    else:
        avg_w, avg_h = max(40, w // 12), max(60, h // 8)

    min_area = avg_w * avg_h * 0.15
    max_area = avg_w * avg_h * 8.0

    # ── 2. Edge / contour analysis → empty-space candidates ────────────
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Canny(blurred, 35, 110)

    kw = max(3, avg_w // 7)
    kh = max(3, avg_h // 7)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw < 10 or bh < 10:
            continue
        aspect = max(bw, bh) / max(min(bw, bh), 1)
        if aspect > 6:
            continue
        box = (x, y, x + bw, y + bh)
        if any(_iou(box, ex) > 0.25 for ex in all_boxes):
            continue
        all_boxes.append(box)

    # ── 3. NMS: keep larger non-overlapping boxes ───────────────────────
    all_boxes.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
    kept: list[tuple[int, int, int, int]] = []
    for box in all_boxes:
        if any(_iou(box, k) > 0.35 for k in kept):
            continue
        kept.append(box)
        if len(kept) >= max_slots:
            break

    # ── 4. Sort top→bottom, left→right; label A1 … Z5 ─────────────────
    row_h = max(avg_h // 2, 20)
    kept.sort(key=lambda b: (b[1] // row_h, b[0]))

    LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = []
    for i, (x1, y1, x2, y2) in enumerate(kept):
        row = LETTERS[min(i // 5, len(LETTERS) - 1)]
        col = (i % 5) + 1
        result.append({
            "id": i + 1,
            "slot_number": f"{row}{col}",
            "polygon": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
            "slot_type": "regular",
            "hourly_rate": 50.0,
        })

    return result
