from fastapi import APIRouter
from services.pnl_service import (
    get_pnl_summary,
    get_pnl_by_day,
    get_pnl_by_symbol,
    get_pnl_chart,
)

router = APIRouter()

@router.get("")
@router.get("/")
@router.get("/summary")
def pnl_summary():
    """
    Tổng hợp PnL toàn hệ thống.
    """
    return get_pnl_summary()

@router.get("/by_day")
def pnl_by_day():
    """
    PnL từng ngày.
    """
    return get_pnl_by_day()

@router.get("/by_symbol")
def pnl_by_symbol():
    """
    PnL theo từng mã giao dịch/sản phẩm.
    """
    return get_pnl_by_symbol()

@router.get("/chart")
def pnl_chart():
    """
    Dữ liệu PnL cho chart frontend.
    """
    return get_pnl_chart()