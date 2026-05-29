from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models import Slot
from backend.app.state import app_state

router = APIRouter(prefix="/slots", tags=["slots"])


def _build_slot_response(slot: Slot, state_map: dict) -> dict:
    state = state_map.get(slot.slot_number, {})
    return {
        "id": slot.id,
        "slot_number": slot.slot_number,
        "polygon": slot.polygon,
        "slot_type": slot.slot_type,
        "hourly_rate": slot.hourly_rate,
        "occupied": state.get("occupied", False),
        "track_id": state.get("track_id", -1),
        "dwell_seconds": state.get("dwell_seconds", 0.0),
    }


@router.get("")
def list_slots(db: Session = Depends(get_db)):
    slots = db.query(Slot).all()
    snapshot = app_state.get_snapshot()
    state_map = {s.slot_number: s.__dict__ for s in snapshot["slot_states"]}
    return [_build_slot_response(s, state_map) for s in slots]


@router.get("/{slot_id}")
def get_slot(slot_id: int, db: Session = Depends(get_db)):
    slot = db.get(Slot, slot_id)
    if not slot:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Slot not found")
    snapshot = app_state.get_snapshot()
    state_map = {s.slot_number: s.__dict__ for s in snapshot["slot_states"]}
    return _build_slot_response(slot, state_map)
