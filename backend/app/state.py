"""Shared in-process application state.

AppState is a singleton passed into the pipeline worker and read by API routers.
Using a simple dataclass + lock instead of Redis keeps the single-process
deployment zero-dependency while still being thread-safe.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from cv.slot_manager import SlotState


@dataclass
class AppState:
    slot_states: list[SlotState] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    fps: float = 0.0
    backend: str = "pytorch"
    latest_jpeg: bytes = b""
    uptime_start: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update(
        self,
        slot_states: list[SlotState],
        stats: dict,
        fps: float,
        backend: str,
        jpeg: bytes,
    ) -> None:
        with self._lock:
            self.slot_states = slot_states
            self.stats = stats
            self.fps = fps
            self.backend = backend
            self.latest_jpeg = jpeg

    def get_snapshot(self) -> dict:
        with self._lock:
            return {
                "slot_states": list(self.slot_states),
                "stats": dict(self.stats),
                "fps": self.fps,
                "backend": self.backend,
                "uptime_seconds": time.time() - self.uptime_start,
            }

    def get_jpeg(self) -> bytes:
        with self._lock:
            return self.latest_jpeg


# Module-level singleton — imported by routers and pipeline worker
app_state = AppState()
