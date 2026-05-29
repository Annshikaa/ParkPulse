from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

import numpy as np
from shapely.geometry import Polygon, box as shapely_box

from cv.detector import Detection


EventType = Literal["enter", "exit"]


@dataclass
class SlotEvent:
    slot_id: int
    event_type: EventType
    track_id: int
    dwell_seconds: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class SlotState:
    slot_id: int
    slot_number: str
    polygon: list[list[float]]
    slot_type: str
    hourly_rate: float
    occupied: bool = False
    track_id: int = -1
    enter_time: float = 0.0
    dwell_seconds: float = 0.0
    # hysteresis counters
    occupy_counter: int = 0
    free_counter: int = 0


class SlotManager:
    """Manages parking slot occupancy using IoU-based detection.

    Uses asymmetric hysteresis (5 frames to mark occupied, 10 to free)
    because false positives (ghost occupancy) are more disruptive to users
    than a slightly delayed free signal.
    IoU over bbox-center: correctly handles partial overlaps and perspective
    distortion — a vehicle touching a slot boundary doesn't trigger occupancy.
    """

    def __init__(
        self,
        slots_path: Path,
        occupancy_iou_threshold: float = 0.15,
        enter_frames: int = 5,
        exit_frames: int = 10,
        event_callback: Callable[[SlotEvent], None] | None = None,
    ) -> None:
        self.occupancy_iou_threshold = occupancy_iou_threshold
        self.enter_frames = enter_frames
        self.exit_frames = exit_frames
        self.event_callback = event_callback

        self._slots: dict[int, SlotState] = {}
        self._slot_polygons: dict[int, Polygon] = {}
        self._dwell_totals: list[float] = []  # completed dwell times for avg calculation

        self._load_slots(slots_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, detections: list[Detection]) -> list[SlotEvent]:
        """Process one frame of detections, return any new events emitted."""
        events: list[SlotEvent] = []

        # Map each slot to the best overlapping detection
        slot_to_best: dict[int, tuple[float, Detection]] = {}
        for det in detections:
            det_poly = self._detection_to_polygon(det)
            for slot_id, slot_poly in self._slot_polygons.items():
                iou = self._compute_iou(det_poly, slot_poly)
                if iou >= self.occupancy_iou_threshold:
                    if slot_id not in slot_to_best or iou > slot_to_best[slot_id][0]:
                        slot_to_best[slot_id] = (iou, det)

        now = time.time()
        for slot_id, slot in self._slots.items():
            if slot_id in slot_to_best:
                _, best_det = slot_to_best[slot_id]
                events += self._handle_vehicle_present(slot, best_det, now)
            else:
                events += self._handle_vehicle_absent(slot, now)

        for ev in events:
            if self.event_callback:
                self.event_callback(ev)

        return events

    def get_slot_states(self) -> list[SlotState]:
        return list(self._slots.values())

    def get_slot(self, slot_id: int) -> SlotState | None:
        return self._slots.get(slot_id)

    def stats(self) -> dict:
        slots = list(self._slots.values())
        occupied = sum(1 for s in slots if s.occupied)
        total = len(slots)
        avg_dwell = (
            sum(self._dwell_totals) / len(self._dwell_totals)
            if self._dwell_totals
            else 0.0
        )
        return {
            "total": total,
            "occupied": occupied,
            "free": total - occupied,
            "occupancy_rate": occupied / total if total else 0.0,
            "avg_dwell_seconds": avg_dwell,
        }

    # ------------------------------------------------------------------
    # Hysteresis state machine
    # ------------------------------------------------------------------

    def _handle_vehicle_present(
        self, slot: SlotState, det: Detection, now: float
    ) -> list[SlotEvent]:
        events: list[SlotEvent] = []
        slot.free_counter = 0  # reset exit countdown

        if slot.occupied:
            slot.dwell_seconds = now - slot.enter_time
            return events

        slot.occupy_counter += 1
        if slot.occupy_counter >= self.enter_frames:
            slot.occupied = True
            slot.track_id = det.track_id
            slot.enter_time = now
            slot.dwell_seconds = 0.0
            slot.occupy_counter = 0
            ev = SlotEvent(
                slot_id=slot.slot_id,
                event_type="enter",
                track_id=det.track_id,
                dwell_seconds=0.0,
                timestamp=now,
            )
            events.append(ev)
        return events

    def _handle_vehicle_absent(self, slot: SlotState, now: float) -> list[SlotEvent]:
        events: list[SlotEvent] = []
        slot.occupy_counter = 0  # reset entry countdown

        if not slot.occupied:
            return events

        slot.free_counter += 1
        if slot.free_counter >= self.exit_frames:
            dwell = now - slot.enter_time
            self._dwell_totals.append(dwell)
            if len(self._dwell_totals) > 1000:  # cap memory
                self._dwell_totals = self._dwell_totals[-500:]

            ev = SlotEvent(
                slot_id=slot.slot_id,
                event_type="exit",
                track_id=slot.track_id,
                dwell_seconds=dwell,
                timestamp=now,
            )
            slot.occupied = False
            slot.track_id = -1
            slot.dwell_seconds = 0.0
            slot.free_counter = 0
            events.append(ev)
        return events

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detection_to_polygon(det: Detection) -> Polygon:
        return shapely_box(det.x1, det.y1, det.x2, det.y2)

    @staticmethod
    def _compute_iou(a: Polygon, b: Polygon) -> float:
        if not a.is_valid or not b.is_valid:
            return 0.0
        intersection = a.intersection(b).area
        if intersection == 0:
            return 0.0
        union = a.union(b).area
        return intersection / union if union > 0 else 0.0

    # ------------------------------------------------------------------
    # Slot loading
    # ------------------------------------------------------------------

    def _load_slots(self, path: Path) -> None:
        with open(path) as f:
            data = json.load(f)
        for s in data:
            sid = s["id"]
            self._slots[sid] = SlotState(
                slot_id=sid,
                slot_number=s["slot_number"],
                polygon=s["polygon"],
                slot_type=s.get("slot_type", "regular"),
                hourly_rate=s.get("hourly_rate", 50.0),
            )
            self._slot_polygons[sid] = Polygon(s["polygon"])
