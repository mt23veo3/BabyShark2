from fastapi import APIRouter, Query
from services.orders_service import (
    get_all_orders,
    get_open_orders,
    get_closed_orders,
    get_order_by_id,
)

router = APIRouter()

@router.get("")
@router.get("/")
def all_orders(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    """
    Danh sách lệnh, mới nhất trên cùng, có trường 'order_time' (opened_at)
    """
    return get_all_orders(page, page_size)

@router.get("/open")
@router.get("/open/")
def open_orders():
    return get_open_orders()

@router.get("/closed")
@router.get("/closed/")
def closed_orders():
    return get_closed_orders()

@router.get("/{order_id}")
@router.get("/{order_id}/")
def order_detail(order_id: str):
    return get_order_by_id(order_id)