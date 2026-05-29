from __future__ import annotations

import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
import structlog

from cv.config import CVConfig, cv_config
from cv.detector import BackendName, Detector
from cv.preprocessor import Preprocessor
from cv.slot_manager import SlotEvent, SlotManager, SlotState
from cv.visualizer import Visualizer

log = structlog.get_logger(__name__)


class ParkPulsePipeline:
    """End-to-end CV pipeline: capture → preprocess → detect → track → slots → visualize.

    Yields (jpeg_bytes, slot_states, events, stats, fps) on every processed frame.
    Thread-safe backend switching via switch_backend().
    Accepts both file paths and RTSP URLs in video_source — cv2.VideoCapture handles both.
    """

    def __init__(
        self,
        config: CVConfig | None = None,
        event_callback: Callable[[SlotEvent], None] | None = None,
    ) -> None:
        self.cfg = config or cv_config
        self._preprocessor = Preprocessor(enabled=self.cfg.preprocessor_enabled)
        self._detector = Detector(
            backend=self.cfg.default_backend,
            weights=self.cfg.weights_path,
            conf=self.cfg.conf_threshold,
            iou=self.cfg.iou_threshold,
        )
        self._slot_manager = SlotManager(
            slots_path=self.cfg.slots_path,
            occupancy_iou_threshold=self.cfg.occupancy_iou_threshold,
            enter_frames=self.cfg.enter_frames,
            exit_frames=self.cfg.exit_frames,
            event_callback=event_callback,
        )
        self._visualizer = Visualizer()
        self._lock = threading.Lock()
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def backend(self) -> BackendName:
        return self._detector.backend

    @property
    def preprocessor_enabled(self) -> bool:
        return self._preprocessor.enabled

    def switch_backend(self, name: BackendName) -> None:
        with self._lock:
            self._detector.switch_backend(name)

    def set_preprocessor(self, enabled: bool) -> None:
        self._preprocessor.enabled = enabled

    def frames(
        self, booked_slot_ids: set[int] | None = None
    ) -> Generator[tuple[bytes, list[SlotState], list[SlotEvent], dict, float], None, None]:
        """Generate annotated JPEG frames forever (or until video ends then loops)."""
        self._running = True
        fps_ema = 0.0
        alpha = 0.3  # EMA smoothing — converges in ~10 frames

        while self._running:
            cap = self._open_capture()
            if cap is None:
                time.sleep(1.0)
                continue

            try:
                while self._running:
                    t0 = time.perf_counter()
                    ret, frame = cap.read()
                    if not ret:
                        log.info("video_end_or_disconnect", source=self.cfg.video_source)
                        break  # file ended → re-open (loop); RTSP → reconnect

                    with self._lock:
                        frame = self._preprocessor.apply(frame)
                        detections = self._detector.detect(frame)
                        backend_name = self._detector.backend

                    events = self._slot_manager.update(detections)
                    slot_states = self._slot_manager.get_slot_states()
                    stats = self._slot_manager.stats()

                    annotated = self._visualizer.draw(
                        frame,
                        slot_states,
                        detections,
                        fps_ema,
                        backend_name,
                        booked_slot_ids,
                    )

                    _, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])

                    elapsed = time.perf_counter() - t0
                    if fps_ema == 0.0:
                        fps_ema = 1.0 / max(elapsed, 1e-6)
                    else:
                        fps_ema = alpha * (1.0 / max(elapsed, 1e-6)) + (1 - alpha) * fps_ema

                    stats["fps"] = round(fps_ema, 1)
                    stats["backend"] = backend_name

                    yield jpeg.tobytes(), slot_states, events, stats, fps_ema
            finally:
                cap.release()

    def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------

    def _open_capture(self) -> cv2.VideoCapture | None:
        src = self.cfg.video_source
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            log.error("capture_open_failed", source=src)
            return None
        log.info("capture_opened", source=src)
        return cap
