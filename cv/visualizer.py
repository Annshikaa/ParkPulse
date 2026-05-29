from __future__ import annotations

import cv2
import numpy as np

from cv.detector import Detection
from cv.slot_manager import SlotState


# Colors (BGR)
COLOR_FREE = (50, 200, 50)
COLOR_OCCUPIED = (40, 40, 220)
COLOR_BOOKED = (200, 150, 0)
COLOR_OVERLAY_ALPHA = 0.35
COLOR_HUD_BG = (20, 20, 20)
COLOR_WHITE = (255, 255, 255)
COLOR_YELLOW = (0, 220, 220)


class Visualizer:
    """Renders slot overlays, vehicle bboxes, track IDs, and HUD onto frames."""

    def draw(
        self,
        frame: np.ndarray,
        slot_states: list[SlotState],
        detections: list[Detection],
        fps: float,
        backend: str,
        booked_slot_ids: set[int] | None = None,
    ) -> np.ndarray:
        out = frame.copy()
        booked = booked_slot_ids or set()

        out = self._draw_slots(out, slot_states, booked)
        out = self._draw_detections(out, detections)
        out = self._draw_hud(out, slot_states, fps, backend)
        return out

    # ------------------------------------------------------------------

    def _draw_slots(
        self, frame: np.ndarray, slots: list[SlotState], booked: set[int]
    ) -> np.ndarray:
        overlay = frame.copy()
        for slot in slots:
            pts = np.array(slot.polygon, dtype=np.int32)
            if slot.slot_id in booked and not slot.occupied:
                color = COLOR_BOOKED
            elif slot.occupied:
                color = COLOR_OCCUPIED
            else:
                color = COLOR_FREE

            cv2.fillPoly(overlay, [pts], color)
            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)

            # Label: slot number + dwell timer
            cx = int(np.mean(pts[:, 0]))
            cy = int(np.mean(pts[:, 1]))
            label = slot.slot_number
            if slot.occupied and slot.dwell_seconds > 0:
                mins = int(slot.dwell_seconds // 60)
                secs = int(slot.dwell_seconds % 60)
                label = f"{slot.slot_number}\n{mins:02d}:{secs:02d}"

            # Scale font size based on polygon area so text is visible at any resolution
            area = cv2.contourArea(pts)
            font_scale = max(0.4, min(1.2, (area ** 0.5) / 80))
            self._put_text_centered(frame, label, cx, cy, font_scale=font_scale)

        cv2.addWeighted(overlay, COLOR_OVERLAY_ALPHA, frame, 1 - COLOR_OVERLAY_ALPHA, 0, frame)
        return frame

    def _draw_detections(self, frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
        for det in detections:
            x1, y1, x2, y2 = int(det.x1), int(det.y1), int(det.x2), int(det.y2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_YELLOW, 2)
            if det.track_id != -1:
                cv2.putText(
                    frame,
                    f"T{det.track_id}",
                    (x1, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    COLOR_YELLOW,
                    1,
                    cv2.LINE_AA,
                )
        return frame

    def _draw_hud(
        self, frame: np.ndarray, slots: list[SlotState], fps: float, backend: str
    ) -> np.ndarray:
        occupied = sum(1 for s in slots if s.occupied)
        total = len(slots)
        lines = [
            f"Occupied: {occupied}/{total}",
            f"FPS: {fps:.1f}",
            f"Backend: {backend}",
        ]
        # Scale HUD to frame size so it's readable at 4K
        h = frame.shape[0]
        font_scale = max(0.55, h / 1080)
        thickness = max(1, int(font_scale))
        line_h = int(30 * font_scale)
        pad = int(12 * font_scale)
        box_h = len(lines) * line_h + pad * 2
        box_w = int(320 * font_scale)
        cv2.rectangle(frame, (0, 0), (box_w, box_h), COLOR_HUD_BG, -1)
        for i, line in enumerate(lines):
            cv2.putText(
                frame, line,
                (pad, pad + (i + 1) * line_h - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale, COLOR_WHITE, thickness, cv2.LINE_AA,
            )
        return frame

    @staticmethod
    def _put_text_centered(frame: np.ndarray, text: str, cx: int, cy: int, font_scale: float = 0.45) -> None:
        lines = text.split("\n")
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = font_scale
        thickness = max(1, int(font_scale * 2))
        line_heights = [cv2.getTextSize(l, font, scale, thickness)[0][1] for l in lines]
        total_h = sum(line_heights) + 4 * (len(lines) - 1)
        y = cy - total_h // 2
        for line in lines:
            (tw, th), _ = cv2.getTextSize(line, font, scale, thickness)
            cv2.putText(
                frame,
                line,
                (cx - tw // 2, y + th),
                font,
                scale,
                COLOR_WHITE,
                thickness,
                cv2.LINE_AA,
            )
            y += th + 4
