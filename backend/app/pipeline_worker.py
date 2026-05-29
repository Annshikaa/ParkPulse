"""Background daemon thread running the CV pipeline."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import structlog

from cv.config import CVConfig
from cv.pipeline import ParkPulsePipeline
from cv.slot_manager import SlotEvent

log = structlog.get_logger(__name__)

SNAPSHOT_INTERVAL_SECONDS = 10


class PipelineWorker:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._pipeline: ParkPulsePipeline | None = None
        self._running = False
        self._last_snapshot_time = 0.0
        self._video_source_override: str | None = None

    # ──────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="cv-pipeline")
        self._thread.start()
        log.info("pipeline_worker_started")

    def stop(self) -> None:
        self._running = False
        if self._pipeline:
            self._pipeline.stop()

    def restart_with_source(self, video_source: str) -> None:
        """Stop pipeline and restart with a new video source (RTSP / file / webcam)."""
        log.info("pipeline_restarting", new_source=video_source)
        self._video_source_override = video_source
        self.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=8.0)
        self._pipeline = None
        self._running = False
        self.start()

    def reload_slots(self) -> None:
        """Restart so the pipeline picks up the newly written slots JSON."""
        src = self._video_source_override
        if src is None:
            from backend.app.config import settings
            src = settings.video_source
        self.restart_with_source(src)

    # ──────────────────────────────────────────────────────────────────
    # Hot-swap controls (no restart needed)
    # ──────────────────────────────────────────────────────────────────

    def switch_backend(self, name: str) -> None:
        if self._pipeline:
            self._pipeline.switch_backend(name)

    def set_preprocessor(self, enabled: bool) -> None:
        if self._pipeline:
            self._pipeline.set_preprocessor(enabled)

    # ──────────────────────────────────────────────────────────────────
    # Internal run loop
    # ──────────────────────────────────────────────────────────────────

    def _run(self) -> None:
        from backend.app.state import app_state
        from backend.app.db.session import SessionLocal
        from backend.app.config import settings

        video_source = self._video_source_override or settings.video_source
        cv_cfg = CVConfig(
            video_source=video_source,
            slots_path=settings.slots_path,
        )
        self._pipeline = ParkPulsePipeline(config=cv_cfg)

        log.info("pipeline_loop_starting", source=video_source)
        try:
            for jpeg, slot_states, events, stats, fps in self._pipeline.frames():
                if not self._running:
                    break

                backend = self._pipeline.backend
                app_state.update(slot_states, stats, fps, backend, jpeg)

                if events:
                    self._persist_events(events, SessionLocal)
                    self._handle_early_departures(events, SessionLocal)

                now = time.time()
                if now - self._last_snapshot_time >= SNAPSHOT_INTERVAL_SECONDS:
                    self._persist_snapshot(stats, fps, backend, SessionLocal)
                    self._last_snapshot_time = now

        except Exception:
            log.exception("pipeline_worker_crashed")
        finally:
            log.info("pipeline_worker_stopped")

    # ──────────────────────────────────────────────────────────────────
    # Early departure: CV exit event → auto-complete active booking
    # ──────────────────────────────────────────────────────────────────

    def _handle_early_departures(self, events: list[SlotEvent], SessionLocal) -> None:
        exit_slot_ids = [ev.slot_id for ev in events if ev.event_type == "exit"]
        if not exit_slot_ids:
            return

        from backend.app.db.models import Booking, Slot

        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            for slot_id in exit_slot_ids:
                # Find a booking that is currently active/confirmed for this slot
                booking = (
                    db.query(Booking)
                    .filter(
                        Booking.slot_id == slot_id,
                        Booking.status.in_(["active", "confirmed"]),
                        Booking.booked_from <= now,
                        Booking.booked_until >= now,
                    )
                    .first()
                )
                if not booking:
                    continue

                actual_hours = max(
                    0.25,  # minimum 15-minute charge
                    (now - booking.booked_from).total_seconds() / 3600,
                )
                slot = db.get(Slot, slot_id)
                rate = slot.hourly_rate if slot else 50.0

                booking.status = "completed"
                booking.actual_exit_time = now
                booking.final_amount = round(actual_hours * rate, 2)
                log.info(
                    "early_departure_autocomplete",
                    slot_id=slot_id,
                    booking_id=booking.id,
                    actual_hours=round(actual_hours, 2),
                    final_amount=booking.final_amount,
                )
            db.commit()
        except Exception:
            log.exception("early_departure_handler_failed")
            db.rollback()
        finally:
            db.close()

    # ──────────────────────────────────────────────────────────────────
    # Persistence helpers
    # ──────────────────────────────────────────────────────────────────

    def _persist_events(self, events: list[SlotEvent], SessionLocal) -> None:
        from backend.app.db.models import CVEvent

        db = SessionLocal()
        try:
            for ev in events:
                db.add(CVEvent(
                    slot_id=ev.slot_id,
                    event_type=ev.event_type,
                    track_id=ev.track_id,
                    dwell_seconds=ev.dwell_seconds,
                    timestamp=datetime.fromtimestamp(ev.timestamp, tz=timezone.utc),
                ))
            db.commit()
        except Exception:
            log.exception("event_persist_failed")
            db.rollback()
        finally:
            db.close()

    def _persist_snapshot(self, stats: dict, fps: float, backend: str, SessionLocal) -> None:
        from backend.app.db.models import OccupancySnapshot

        db = SessionLocal()
        try:
            db.add(OccupancySnapshot(
                timestamp=datetime.now(timezone.utc),
                occupied_count=stats.get("occupied", 0),
                total_count=stats.get("total", 0),
                occupancy_rate=stats.get("occupancy_rate", 0.0),
                backend=backend,
                fps=fps,
            ))
            db.commit()
        except Exception:
            log.exception("snapshot_persist_failed")
            db.rollback()
        finally:
            db.close()


pipeline_worker = PipelineWorker()
