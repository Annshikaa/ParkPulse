"""Admin-only backend, CCTV source, and slot configuration control."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal

import cv2
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.dependencies import get_current_admin
from backend.app.db.models import User
from backend.app.db.session import SessionLocal
from backend.app.pipeline_worker import pipeline_worker
from backend.app.state import app_state

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

BACKENDS = ["pytorch", "onnx_fp32", "onnx_int8"]
BENCHMARK_PATH = Path("docs/benchmark_results.json")
SLOTS_PATH = Path("data/parking_slots.json")


# ──────────────────────────────────────────────────────────────────────────
# GET /settings  — current config snapshot
# ──────────────────────────────────────────────────────────────────────────

@router.get("")
def get_settings(_: User = Depends(get_current_admin)):
    benchmarks = []
    if BENCHMARK_PATH.exists():
        try:
            benchmarks = json.loads(BENCHMARK_PATH.read_text())
        except Exception:
            pass

    snapshot = app_state.get_snapshot()
    from backend.app.config import settings as app_settings

    current_source = pipeline_worker._video_source_override or app_settings.video_source
    slot_count = len(snapshot["slot_states"])

    return {
        "current_backend": snapshot["backend"],
        "available_backends": BACKENDS,
        "fps": snapshot["fps"],
        "preprocessor_enabled": True,
        "benchmarks": benchmarks,
        "video_source": current_source,
        "slot_count": slot_count,
    }


# ──────────────────────────────────────────────────────────────────────────
# POST /settings/backend
# ──────────────────────────────────────────────────────────────────────────

class BackendSwitchRequest(BaseModel):
    backend: str


@router.post("/backend")
def switch_backend(body: BackendSwitchRequest, _: User = Depends(get_current_admin)):
    if body.backend not in BACKENDS:
        raise HTTPException(status_code=400, detail=f"Unknown backend: {body.backend}")
    pipeline_worker.switch_backend(body.backend)
    time.sleep(0.5)
    snapshot = app_state.get_snapshot()
    return {"backend": snapshot["backend"], "fps": snapshot["fps"], "message": f"Switched to {body.backend}"}


# ──────────────────────────────────────────────────────────────────────────
# POST /settings/preprocessor
# ──────────────────────────────────────────────────────────────────────────

class PreprocessorRequest(BaseModel):
    enabled: bool


@router.post("/preprocessor")
def toggle_preprocessor(body: PreprocessorRequest, _: User = Depends(get_current_admin)):
    pipeline_worker.set_preprocessor(body.enabled)
    return {"preprocessor_enabled": body.enabled}


# ──────────────────────────────────────────────────────────────────────────
# POST /settings/video-source  — connect CCTV / switch feed
# ──────────────────────────────────────────────────────────────────────────

class VideoSourceRequest(BaseModel):
    source: str  # RTSP URL, file path, or "0" for webcam


@router.post("/video-source")
def set_video_source(body: VideoSourceRequest, _: User = Depends(get_current_admin)):
    src = body.source.strip()
    if not src:
        raise HTTPException(status_code=400, detail="source must not be empty")

    # Quick reachability check (1-second timeout)
    raw_src = int(src) if src.isdigit() else src
    cap = cv2.VideoCapture(raw_src)
    # Give RTSP streams a moment
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    opened = cap.isOpened()
    cap.release()
    if not opened:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot open video source '{src}'. Check the URL/path and try again.",
        )

    # Restart pipeline on new source in a background thread so the HTTP
    # response returns immediately (restart takes a few seconds).
    import threading
    threading.Thread(
        target=pipeline_worker.restart_with_source,
        args=(src,),
        daemon=True,
    ).start()

    log.info("video_source_changed", source=src)
    return {"message": f"Pipeline switching to: {src}", "source": src}


# ──────────────────────────────────────────────────────────────────────────
# GET /settings/detect-slots  — auto-detect slots from current frame
# ──────────────────────────────────────────────────────────────────────────

@router.get("/snapshot")
def get_snapshot(_: User = Depends(get_current_admin)):
    """Return a JPEG snapshot from the active video source for the slot editor."""
    from fastapi.responses import Response
    from backend.app.config import settings as app_settings

    src = pipeline_worker._video_source_override or app_settings.video_source
    raw_src = int(src) if str(src).isdigit() else src

    cap = cv2.VideoCapture(raw_src)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise HTTPException(status_code=503, detail="Cannot capture frame from video source")

    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return Response(content=buf.tobytes(), media_type="image/jpeg")


@router.get("/detect-slots")
def detect_slots_from_feed(_: User = Depends(get_current_admin)):
    """Capture one frame from the active video source and run auto-detection."""
    from backend.app.config import settings as app_settings
    from cv.auto_slot_detector import detect_slots

    src = pipeline_worker._video_source_override or app_settings.video_source
    raw_src = int(src) if str(src).isdigit() else src

    cap = cv2.VideoCapture(raw_src)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise HTTPException(status_code=503, detail="Could not capture frame from video source")

    # Get current YOLO detections from live pipeline state as anchors
    snapshot = app_state.get_snapshot()
    # We don't have Detection objects here, only SlotState — pass None
    # The detector will use image analysis only
    slots = detect_slots(frame, detections=None)

    log.info("slots_auto_detected", count=len(slots))
    return {"detected": len(slots), "slots": slots}


# ──────────────────────────────────────────────────────────────────────────
# POST /settings/slots  — save detected slots and reload pipeline
# ──────────────────────────────────────────────────────────────────────────

class SaveSlotsRequest(BaseModel):
    slots: list[dict]


@router.post("/slots")
def save_slots(body: SaveSlotsRequest, _: User = Depends(get_current_admin)):
    if not body.slots:
        raise HTTPException(status_code=400, detail="slots list is empty")

    # Normalise: ensure required fields
    normalised = []
    for i, s in enumerate(body.slots):
        normalised.append({
            "id": i + 1,
            "slot_number": s.get("slot_number", f"S{i+1}"),
            "polygon": s["polygon"],
            "slot_type": s.get("slot_type", "regular"),
            "hourly_rate": float(s.get("hourly_rate", 50.0)),
        })

    SLOTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SLOTS_PATH.write_text(json.dumps(normalised, indent=2))

    # Also sync slots to DB
    _sync_slots_to_db(normalised)

    # Restart pipeline so it picks up the new slot file
    import threading
    threading.Thread(target=pipeline_worker.reload_slots, daemon=True).start()

    log.info("slots_saved", count=len(normalised))
    return {"message": f"Saved {len(normalised)} slots. Pipeline reloading…", "count": len(normalised)}


def _sync_slots_to_db(slots: list[dict]) -> None:
    """Upsert slot records in the DB so bookings can reference them."""
    from backend.app.db.models import Slot

    db = SessionLocal()
    try:
        existing_ids = {s.id for s in db.query(Slot.id).all()}
        new_ids = {s["id"] for s in slots}

        for s in slots:
            if s["id"] in existing_ids:
                row = db.get(Slot, s["id"])
                row.slot_number = s["slot_number"]
                row.polygon_json = json.dumps(s["polygon"])
                row.slot_type = s["slot_type"]
                row.hourly_rate = s["hourly_rate"]
            else:
                db.add(Slot(
                    id=s["id"],
                    slot_number=s["slot_number"],
                    polygon_json=json.dumps(s["polygon"]),
                    slot_type=s["slot_type"],
                    hourly_rate=s["hourly_rate"],
                ))

        # Remove slots that no longer exist (only if they have no bookings)
        for old_id in existing_ids - new_ids:
            from backend.app.db.models import Booking
            has_bookings = db.query(Booking).filter(Booking.slot_id == old_id).first()
            if not has_bookings:
                db.delete(db.get(Slot, old_id))

        db.commit()
    except Exception:
        log.exception("slot_db_sync_failed")
        db.rollback()
    finally:
        db.close()
