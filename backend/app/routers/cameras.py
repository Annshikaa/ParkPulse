"""Camera CRUD and per-camera pipeline management."""
from __future__ import annotations

import threading

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.dependencies import get_current_admin, get_db
from backend.app.db.models import Camera, User
from backend.app.camera_manager import camera_manager

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/cameras", tags=["cameras"])


# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────

class CameraCreate(BaseModel):
    name: str
    rtsp_url: str
    location: str | None = None


class CameraUpdate(BaseModel):
    name: str | None = None
    rtsp_url: str | None = None
    location: str | None = None
    is_active: bool | None = None


class CameraOut(BaseModel):
    id: int
    name: str
    rtsp_url: str
    location: str | None
    status: str
    is_active: bool

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────────────────────────────────────
# GET /cameras
# ──────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[CameraOut])
def list_cameras(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    cameras = db.query(Camera).order_by(Camera.id).all()
    # Enrich status from live camera_manager
    for cam in cameras:
        live = camera_manager.get_status(cam.id)
        if live:
            cam.status = live
    return cameras


# ──────────────────────────────────────────────────────────────────────────────
# POST /cameras
# ──────────────────────────────────────────────────────────────────────────────

@router.post("", response_model=CameraOut, status_code=201)
def create_camera(body: CameraCreate, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    cam = Camera(name=body.name, rtsp_url=body.rtsp_url, location=body.location)
    db.add(cam)
    db.commit()
    db.refresh(cam)
    # Start a worker for this camera
    threading.Thread(target=camera_manager.start_camera, args=(cam.id, cam.rtsp_url), daemon=True).start()
    log.info("camera_created", camera_id=cam.id, name=cam.name)
    return cam


# ──────────────────────────────────────────────────────────────────────────────
# GET /cameras/{camera_id}
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    live = camera_manager.get_status(camera_id)
    if live:
        cam.status = live
    return cam


# ──────────────────────────────────────────────────────────────────────────────
# PUT /cameras/{camera_id}
# ──────────────────────────────────────────────────────────────────────────────

@router.put("/{camera_id}", response_model=CameraOut)
def update_camera(camera_id: int, body: CameraUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    rtsp_changed = body.rtsp_url is not None and body.rtsp_url != cam.rtsp_url
    if body.name is not None:
        cam.name = body.name
    if body.rtsp_url is not None:
        cam.rtsp_url = body.rtsp_url
    if body.location is not None:
        cam.location = body.location
    if body.is_active is not None:
        cam.is_active = body.is_active

    db.commit()
    db.refresh(cam)

    if rtsp_changed or (body.is_active is not None):
        if cam.is_active:
            threading.Thread(
                target=camera_manager.restart_camera,
                args=(cam.id, cam.rtsp_url),
                daemon=True,
            ).start()
        else:
            camera_manager.stop_camera(cam.id)

    log.info("camera_updated", camera_id=cam.id)
    return cam


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /cameras/{camera_id}
# ──────────────────────────────────────────────────────────────────────────────

@router.delete("/{camera_id}", status_code=204)
def delete_camera(camera_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    camera_manager.stop_camera(camera_id)
    db.delete(cam)
    db.commit()
    log.info("camera_deleted", camera_id=camera_id)


# ──────────────────────────────────────────────────────────────────────────────
# POST /cameras/{camera_id}/restart
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{camera_id}/restart")
def restart_camera(camera_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    threading.Thread(
        target=camera_manager.restart_camera,
        args=(cam.id, cam.rtsp_url),
        daemon=True,
    ).start()
    return {"message": f"Restarting camera {cam.name}"}


# ──────────────────────────────────────────────────────────────────────────────
# GET /cameras/{camera_id}/snapshot  — JPEG frame from this camera
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{camera_id}/snapshot")
def get_camera_snapshot(camera_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    import cv2
    from fastapi.responses import Response

    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    raw_src = int(cam.rtsp_url) if cam.rtsp_url.isdigit() else cam.rtsp_url
    cap = cv2.VideoCapture(raw_src)
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise HTTPException(status_code=503, detail="Cannot capture frame from camera")

    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return Response(content=buf.tobytes(), media_type="image/jpeg")
