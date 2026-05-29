"""Standalone OpenCV window for the ParkPulse CV pipeline.

Keys:
  q       — quit
  space   — pause / resume
  s       — save snapshot to docs/screenshots/
  1       — switch to PyTorch backend
  2       — switch to ONNX FP32 backend
  3       — switch to ONNX INT8 backend
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# repo root on sys.path so cv.* imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import structlog

from cv.config import CVConfig
from cv.pipeline import ParkPulsePipeline

log = structlog.get_logger(__name__)

BACKEND_KEYS = {ord("1"): "pytorch", ord("2"): "onnx_fp32", ord("3"): "onnx_int8"}
SNAPSHOT_DIR = Path("docs/screenshots")


def main() -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    config = CVConfig()
    pipeline = ParkPulsePipeline(config=config)
    log.info("pipeline_starting", source=config.video_source, backend=config.default_backend)

    paused = False
    last_frame = None

    for jpeg, states, events, stats, fps in pipeline.frames():
        if events:
            for ev in events:
                log.info("slot_event", **{k: v for k, v in ev.__dict__.items()})

        import numpy as _np
        img = cv2.imdecode(_np.frombuffer(jpeg, dtype=_np.uint8), cv2.IMREAD_COLOR)

        # Scale down for display — keeps full-res processing, shrinks only the window
        h, w = img.shape[:2]
        scale = min(1.0, 1280 / w, 720 / h)
        if scale < 1.0:
            disp = cv2.resize(img, (int(w * scale), int(h * scale)))
        else:
            disp = img
        last_frame = disp

        if not paused:
            cv2.imshow("ParkPulse — CV Pipeline", disp)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            log.info("user_quit")
            pipeline.stop()
            break
        elif key == ord(" "):
            paused = not paused
            log.info("paused" if paused else "resumed")
        elif key == ord("s") and last_frame is not None:
            ts = int(time.time())
            path = SNAPSHOT_DIR / f"snapshot_{ts}.jpg"
            cv2.imwrite(str(path), last_frame)
            log.info("snapshot_saved", path=str(path))
        elif key in BACKEND_KEYS:
            new_backend = BACKEND_KEYS[key]
            pipeline.switch_backend(new_backend)
            log.info("backend_switch_requested", backend=new_backend)

    cv2.destroyAllWindows()
    log.info("pipeline_stopped", final_fps=stats.get("fps", 0))


if __name__ == "__main__":
    main()
