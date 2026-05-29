"""FastAPI application entry point."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable when running from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.db.session import create_all_tables
from backend.app.pipeline_worker import pipeline_worker

# Routers
from backend.app.routers.health import router as health_router
from backend.app.routers.auth import router as auth_router
from backend.app.routers.slots import router as slots_router
from backend.app.routers.stats import router as stats_router
from backend.app.routers.stream import router as stream_router
from backend.app.routers.settings import router as settings_router
from backend.app.routers.bookings import router as bookings_router
from backend.app.routers.payments import router as payments_router
from backend.app.routers.analytics import router as analytics_router
from backend.app.routers.admin import router as admin_router
from backend.app.routers.cameras import router as cameras_router
from backend.app.routers.alerts import router as alerts_router

log = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="ParkPulse API",
        version="1.0.0",
        description="Smart parking management — CV-powered slot detection + booking system",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(slots_router)
    app.include_router(stats_router)
    app.include_router(stream_router)
    app.include_router(settings_router)
    app.include_router(bookings_router)
    app.include_router(payments_router)
    app.include_router(analytics_router)
    app.include_router(admin_router)
    app.include_router(cameras_router)
    app.include_router(alerts_router)

    @app.on_event("startup")
    async def startup():
        from backend.app.camera_manager import camera_manager
        from backend.app.db.session import SessionLocal
        from backend.app.db.models import Slot
        import json
        from pathlib import Path

        log.info("creating_db_tables")
        create_all_tables()

        # Auto-sync slots from JSON to DB if DB is empty
        slots_path = Path(settings.slots_path)
        db = SessionLocal()
        try:
            if db.query(Slot).count() == 0 and slots_path.exists():
                slot_data = json.loads(slots_path.read_text())
                for s in slot_data:
                    db.add(Slot(
                        id=s["id"],
                        slot_number=s["slot_number"],
                        polygon_json=json.dumps(s["polygon"]),
                        slot_type=s.get("slot_type", "regular"),
                        hourly_rate=float(s.get("hourly_rate", 50.0)),
                    ))
                db.commit()
                log.info("slots_synced_from_json", count=len(slot_data))
        except Exception:
            log.exception("slot_autosync_failed")
            db.rollback()
        finally:
            db.close()

        log.info("starting_pipeline_worker")
        pipeline_worker.start()
        log.info("booting_camera_manager")
        camera_manager.boot_from_db()
        log.info("startup_complete", video_source=settings.video_source)

    @app.on_event("shutdown")
    async def shutdown():
        from backend.app.camera_manager import camera_manager
        pipeline_worker.stop()
        camera_manager.stop_all()
        log.info("shutdown_complete")

    return app


app = create_app()
