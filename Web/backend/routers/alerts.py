from fastapi import APIRouter, Query
from services.alerts_service import (
    get_all_alerts,
    get_unread_alerts,
    mark_alert_as_read,
)

router = APIRouter()

@router.get("")
@router.get("/")
def all_alerts(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    return get_all_alerts(page, page_size)

@router.get("/unread")
@router.get("/unread/")
def unread_alerts():
    return get_unread_alerts()

@router.post("/read/{alert_id}")
@router.post("/read/{alert_id}/")
def read_alert(alert_id: str):
    return mark_alert_as_read(alert_id)