import time

from fastapi import APIRouter

from backend.app.state import app_state

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats():
    snapshot = app_state.get_snapshot()
    return {
        **snapshot["stats"],
        "fps": snapshot["fps"],
        "backend": snapshot["backend"],
        "uptime_seconds": snapshot["uptime_seconds"],
    }
