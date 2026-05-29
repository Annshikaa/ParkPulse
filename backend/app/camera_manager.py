"""Manages one PipelineWorker per camera, keyed by camera DB id."""
from __future__ import annotations

import threading
from typing import Dict, Optional

import structlog

from backend.app.pipeline_worker import PipelineWorker

log = structlog.get_logger(__name__)


class CameraManager:
    """Thread-safe registry of per-camera pipeline workers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._workers: Dict[int, PipelineWorker] = {}

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def start_camera(self, camera_id: int, rtsp_url: str) -> None:
        """Create and start a new worker for *camera_id*. Idempotent."""
        with self._lock:
            if camera_id in self._workers:
                log.info("camera_already_running", camera_id=camera_id)
                return
            worker = PipelineWorker()
            worker._video_source_override = rtsp_url
            self._workers[camera_id] = worker

        worker.start()
        log.info("camera_worker_started", camera_id=camera_id, source=rtsp_url)

    def stop_camera(self, camera_id: int) -> None:
        """Stop and remove the worker for *camera_id*."""
        with self._lock:
            worker = self._workers.pop(camera_id, None)
        if worker:
            worker.stop()
            log.info("camera_worker_stopped", camera_id=camera_id)

    def restart_camera(self, camera_id: int, rtsp_url: str) -> None:
        """Stop existing worker (if any) then start a new one."""
        self.stop_camera(camera_id)
        self.start_camera(camera_id, rtsp_url)

    def stop_all(self) -> None:
        with self._lock:
            ids = list(self._workers.keys())
        for cid in ids:
            self.stop_camera(cid)

    def get_status(self, camera_id: int) -> Optional[str]:
        """Return 'online' if worker is running, 'offline' otherwise."""
        with self._lock:
            worker = self._workers.get(camera_id)
        if worker is None:
            return "offline"
        return "online" if worker._running else "offline"

    def active_camera_ids(self) -> list[int]:
        with self._lock:
            return list(self._workers.keys())

    # ──────────────────────────────────────────────────────────────────────
    # Bootstrap: start all active cameras from DB on app startup
    # ──────────────────────────────────────────────────────────────────────

    def boot_from_db(self) -> None:
        """Called once at startup — launches a worker for every active Camera row."""
        from backend.app.db.session import SessionLocal
        from backend.app.db.models import Camera

        db = SessionLocal()
        try:
            cameras = db.query(Camera).filter(Camera.is_active == True).all()
            for cam in cameras:
                threading.Thread(
                    target=self.start_camera,
                    args=(cam.id, cam.rtsp_url),
                    daemon=True,
                ).start()
            log.info("camera_manager_booted", count=len(cameras))
        except Exception:
            log.exception("camera_manager_boot_failed")
        finally:
            db.close()


camera_manager = CameraManager()
