"""MJPEG video stream and WebSocket tick stream."""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import structlog

from backend.app.state import app_state

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/stream", tags=["stream"])

# Active WebSocket connections — tracked so we can broadcast CV events
_ws_clients: set[WebSocket] = set()


@router.get("/video")
async def mjpeg_stream():
    """MJPEG stream of annotated frames for browser <img src> or <video>."""

    async def generate():
        while True:
            jpeg = app_state.get_jpeg()
            if jpeg:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                )
            await asyncio.sleep(0.033)  # ~30 fps cap

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    log.info("ws_client_connected", total=len(_ws_clients))
    try:
        while True:
            snapshot = app_state.get_snapshot()
            payload = {
                "type": "tick",
                "stats": snapshot["stats"],
                "fps": snapshot["fps"],
                "backend": snapshot["backend"],
                "slots": [
                    {
                        "slot_id": s.slot_id,
                        "slot_number": s.slot_number,
                        "occupied": s.occupied,
                        "track_id": s.track_id,
                        "dwell_seconds": round(s.dwell_seconds, 1),
                    }
                    for s in snapshot["slot_states"]
                ],
                "timestamp": time.time(),
            }
            await ws.send_text(json.dumps(payload))
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("ws_error")
    finally:
        _ws_clients.discard(ws)
        log.info("ws_client_disconnected", total=len(_ws_clients))


async def broadcast_event(event_data: dict) -> None:
    """Called by pipeline worker when a CV event fires."""
    if not _ws_clients:
        return
    msg = json.dumps({"type": "event", **event_data})
    dead: set[WebSocket] = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)
