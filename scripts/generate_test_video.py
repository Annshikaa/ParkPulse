"""
Generate a synthetic top-down parking lot video for CV pipeline testing.
Produces test_parking.mp4 in the project root — no internet required.

Usage:
    python scripts/generate_test_video.py
"""
import random
import math
import cv2
import numpy as np
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
W, H = 1280, 720
FPS = 25
DURATION_SEC = 120          # 2-minute loop
OUT_PATH = Path(__file__).resolve().parents[1] / "test_parking.mp4"

SLOT_ROWS = [
    # (row_y_center, x_start, slot_count, direction)  direction: 1=top-entry -1=bottom-entry
    (160, 80,  10, 1),
    (300, 80,  10, -1),
    (460, 80,  10, 1),
    (600, 80,  10, -1),
]
SLOT_W, SLOT_H = 88, 46          # each parking bay size (pixels)
SLOT_GAP = 4                     # gap between bays

# Car residence: each car stays 4–20 seconds before leaving
MIN_DWELL_FRAMES = FPS * 4
MAX_DWELL_FRAMES = FPS * 20

# Probability per frame that a free slot gets a new car
ARRIVAL_PROB = 0.008

# ── Build slot grid ───────────────────────────────────────────────────────────
def build_slots():
    slots = []
    sid = 0
    for row_y, x_start, count, _ in SLOT_ROWS:
        for i in range(count):
            x = x_start + i * (SLOT_W + SLOT_GAP)
            y = row_y
            slots.append({
                "id": sid,
                "rect": (x, y - SLOT_H // 2, SLOT_W, SLOT_H),   # x,y,w,h
                "occupied": False,
                "car_color": None,
                "frames_left": 0,
                "entering": False,
                "entry_progress": 0.0,
                "exiting": False,
                "exit_progress": 0.0,
            })
            sid += 1
    return slots

# ── Car colors ────────────────────────────────────────────────────────────────
CAR_COLORS = [
    (220, 60,  60),   # red
    (60,  60,  220),  # blue
    (60,  180, 60),   # green
    (200, 200, 60),   # yellow
    (180, 180, 180),  # silver
    (60,  60,  60),   # dark
    (220, 140, 60),   # orange
    (180, 60,  180),  # purple
    (60,  200, 200),  # teal
    (240, 240, 240),  # white
]

def random_car_color():
    base = random.choice(CAR_COLORS)
    jitter = lambda v: max(0, min(255, v + random.randint(-20, 20)))
    return tuple(jitter(c) for c in base)

# ── Draw asphalt background with lane markings ────────────────────────────────
def draw_background(frame):
    frame[:] = (45, 45, 45)   # dark asphalt

    # Drive lane stripes (dashed yellow center lines between rows)
    lane_ys = [230, 380, 530]
    for ly in lane_ys:
        for x in range(0, W, 30):
            cv2.line(frame, (x, ly), (x + 18, ly), (80, 80, 30), 1)

    # Outer border
    cv2.rectangle(frame, (5, 5), (W - 5, H - 5), (70, 70, 70), 2)

def draw_slot_lines(frame, slots):
    for s in slots:
        x, y, w, h = s["rect"]
        color = (100, 100, 100)
        thickness = 1
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)

def draw_car(frame, rect, color, alpha=1.0):
    x, y, w, h = rect
    car_pad_x, car_pad_y = 6, 5
    cx, cy = x + car_pad_x, y + car_pad_y
    cw, ch = w - car_pad_x * 2, h - car_pad_y * 2
    if cw < 4 or ch < 4:
        return

    overlay = frame.copy()

    # Car body
    cv2.rectangle(overlay, (cx, cy), (cx + cw, cy + ch), color, -1)

    # Windshields
    ww = max(4, cw // 3)
    wh = max(3, ch // 3)
    win_col = (200, 220, 240)
    cv2.rectangle(overlay, (cx + ww, cy + 3), (cx + cw - ww, cy + 3 + wh), win_col, -1)
    cv2.rectangle(overlay, (cx + ww, cy + ch - 3 - wh), (cx + cw - ww, cy + ch - 3), win_col, -1)

    # Wheel dots
    wheel_col = (20, 20, 20)
    wr = max(2, min(4, ch // 5))
    cv2.circle(overlay, (cx + wr + 1, cy + wr + 1), wr, wheel_col, -1)
    cv2.circle(overlay, (cx + cw - wr - 1, cy + wr + 1), wr, wheel_col, -1)
    cv2.circle(overlay, (cx + wr + 1, cy + ch - wr - 1), wr, wheel_col, -1)
    cv2.circle(overlay, (cx + cw - wr - 1, cy + ch - wr - 1), wr, wheel_col, -1)

    # Shadow
    cv2.rectangle(overlay, (cx + 3, cy + ch), (cx + cw + 2, cy + ch + 3), (25, 25, 25), -1)

    if alpha < 1.0:
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    else:
        frame[:] = overlay

# ── Main generation ───────────────────────────────────────────────────────────
def main():
    total_frames = FPS * DURATION_SEC
    slots = build_slots()

    # Pre-occupy ~50% of slots randomly at start
    for s in slots:
        if random.random() < 0.5:
            s["occupied"] = True
            s["car_color"] = random_car_color()
            s["frames_left"] = random.randint(MIN_DWELL_FRAMES, MAX_DWELL_FRAMES)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(OUT_PATH), fourcc, FPS, (W, H))

    print(f"Generating {DURATION_SEC}s parking lot video ({total_frames} frames)…")
    print(f"Output: {OUT_PATH}")

    for frame_idx in range(total_frames):
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        draw_background(frame)
        draw_slot_lines(frame, slots)

        for s in slots:
            x, y, w, h = s["rect"]

            if s["exiting"]:
                # Fade out car
                s["exit_progress"] = min(1.0, s["exit_progress"] + 0.08)
                alpha = 1.0 - s["exit_progress"]
                draw_car(frame, s["rect"], s["car_color"], alpha)
                if s["exit_progress"] >= 1.0:
                    s["exiting"] = False
                    s["occupied"] = False
                    s["car_color"] = None

            elif s["entering"]:
                # Fade in car
                s["entry_progress"] = min(1.0, s["entry_progress"] + 0.08)
                draw_car(frame, s["rect"], s["car_color"], s["entry_progress"])
                if s["entry_progress"] >= 1.0:
                    s["entering"] = False

            elif s["occupied"]:
                draw_car(frame, s["rect"], s["car_color"])
                s["frames_left"] -= 1
                if s["frames_left"] <= 0:
                    # Start exit animation
                    s["exiting"] = True
                    s["exit_progress"] = 0.0

            else:
                # Free slot — maybe a car arrives
                if random.random() < ARRIVAL_PROB:
                    s["occupied"] = True
                    s["car_color"] = random_car_color()
                    s["frames_left"] = random.randint(MIN_DWELL_FRAMES, MAX_DWELL_FRAMES)
                    s["entering"] = True
                    s["entry_progress"] = 0.0

        # HUD
        occupied = sum(1 for s in slots if s["occupied"] or s["entering"])
        total = len(slots)
        occ_text = f"Occupied: {occupied}/{total}"
        cv2.putText(frame, occ_text, (10, H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1)
        ts = f"{frame_idx // (FPS * 60):02d}:{(frame_idx // FPS) % 60:02d}"
        cv2.putText(frame, ts, (W - 70, H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1)

        out.write(frame)

        if frame_idx % (FPS * 10) == 0:
            pct = frame_idx / total_frames * 100
            print(f"  {pct:.0f}%  frame {frame_idx}/{total_frames}")

    out.release()
    print(f"\nDone! Video saved to: {OUT_PATH}")
    print(f"To use it, set video_source in backend/.env or Admin → Settings → Video Source:")
    print(f"  {OUT_PATH}")


if __name__ == "__main__":
    main()
