from fastapi import APIRouter
from services.signals_service import (
    get_all_signals,
    get_signal_by_id,
    get_signal_stats,
)

router = APIRouter()

@router.get("")
@router.get("/")
def all_signals():
    return get_all_signals()

@router.get("/stats")
@router.get("/stats/")
def signal_stats():
    return get_signal_stats()

@router.get("/{signal_id}")
@router.get("/{signal_id}/")
def signal_detail(signal_id: str):
    return get_signal_by_id(signal_id)