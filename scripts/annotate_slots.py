"""Simplified slot annotation — 2 clicks per slot (top-left, bottom-right).

Controls:
  Click 1 : top-left corner of parking bay
  Click 2 : bottom-right corner  →  slot rectangle is drawn instantly
  Enter   : confirm slot and start next one
  U       : undo last confirmed slot
  S       : save and quit
  Q       : quit without saving
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np

VIDEO_SOURCE = "sample_video.mp4"
OUTPUT_PATH = Path("data/parking_slots.json")

SLOT_TYPES = ["regular", "regular", "handicap", "regular", "regular", "ev", "regular", "regular", "regular", "regular"]
HOURLY_RATES = {"regular": 50.0, "handicap": 30.0, "ev": 60.0}
COLORS = [(50,200,50),(200,50,200),(50,200,200),(200,200,50),(200,100,50),(100,50,200),(50,100,200),(200,50,100)]


def main() -> None:
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print(f"ERROR: Could not read {VIDEO_SOURCE}")
        sys.exit(1)

    # Resize display if frame is too large
    h, w = frame.shape[:2]
    scale = min(1.0, 1400 / w, 850 / h)
    disp_w, disp_h = int(w * scale), int(h * scale)
    base = cv2.resize(frame, (disp_w, disp_h)) if scale < 1 else frame.copy()

    completed: list[dict] = []
    pts: list[tuple[int,int]] = []   # current in-progress slot (max 2 points)

    def scale_to_orig(x, y):
        return int(x / scale), int(y / scale)

    def redraw():
        img = base.copy()
        n = len(completed)

        # Draw instruction banner
        msg = f"Slot {n+1}: Click TOP-LEFT corner" if len(pts) == 0 else f"Slot {n+1}: Click BOTTOM-RIGHT corner"
        cv2.rectangle(img, (0,0), (disp_w, 36), (20,20,20), -1)
        cv2.putText(img, msg, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2, cv2.LINE_AA)
        cv2.putText(img, "Enter=confirm  U=undo  S=save  Q=quit", (10, disp_h-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1, cv2.LINE_AA)

        # Draw confirmed slots
        for i, s in enumerate(completed):
            poly = np.array(s["polygon"], dtype=np.int32)
            # scale back to display coords
            display_poly = (poly * scale).astype(np.int32)
            color = COLORS[i % len(COLORS)]
            cv2.polylines(img, [display_poly], True, color, 2)
            cx = int(np.mean(display_poly[:,0]))
            cy = int(np.mean(display_poly[:,1]))
            cv2.putText(img, s["slot_number"], (cx-12, cy+5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

        # Draw current in-progress rectangle
        if len(pts) == 1:
            cv2.circle(img, pts[0], 5, (0,255,255), -1)
        elif len(pts) == 2:
            cv2.rectangle(img, pts[0], pts[1], (0,255,255), 2)

        return img

    state = {"pts": []}

    def mouse_cb(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if len(state["pts"]) < 2:
                state["pts"].append((x, y))

    cv2.namedWindow("Annotate Parking Slots", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Annotate Parking Slots", disp_w, disp_h)
    cv2.setMouseCallback("Annotate Parking Slots", mouse_cb)

    while True:
        pts = state["pts"]
        cv2.imshow("Annotate Parking Slots", redraw())
        key = cv2.waitKey(30) & 0xFF

        # Enter — confirm slot if 2 points drawn
        if key in (13, 10):
            if len(pts) == 2:
                x1 = min(pts[0][0], pts[1][0])
                y1 = min(pts[0][1], pts[1][1])
                x2 = max(pts[0][0], pts[1][0])
                y2 = max(pts[0][1], pts[1][1])

                # Convert display coords back to original video coords
                ox1, oy1 = scale_to_orig(x1, y1)
                ox2, oy2 = scale_to_orig(x2, y2)

                n = len(completed) + 1
                row = chr(64 + (n-1)//3 + 1)
                col = (n-1)%3 + 1
                slot_num = f"{row}{col}"
                idx = (n-1) % len(SLOT_TYPES)
                stype = SLOT_TYPES[idx]

                completed.append({
                    "id": n,
                    "slot_number": slot_num,
                    "polygon": [[ox1,oy1],[ox2,oy1],[ox2,oy2],[ox1,oy2]],
                    "slot_type": stype,
                    "hourly_rate": HOURLY_RATES[stype],
                })
                print(f"  Slot {slot_num} saved ({ox1},{oy1}) → ({ox2},{oy2})")
                state["pts"] = []
            else:
                print("  Draw the rectangle first (2 clicks needed)")

        elif key == ord("u"):
            if completed:
                removed = completed.pop()
                print(f"  Undid {removed['slot_number']}")
            state["pts"] = []

        elif key == ord("s"):
            if not completed:
                print("  No slots drawn yet!")
                continue
            OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_PATH, "w") as f:
                json.dump(completed, f, indent=2)
            print(f"\nSaved {len(completed)} slots to {OUTPUT_PATH}")
            break

        elif key == ord("q"):
            print("Quit without saving.")
            break

    cv2.destroyAllWindows()
    print("\nDone! Now run: python scripts/run_standalone.py")


if __name__ == "__main__":
    main()
