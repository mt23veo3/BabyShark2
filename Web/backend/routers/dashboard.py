from fastapi import APIRouter
from services.dashboard_service import (
    get_total_equity,
    get_total_pnl,
    get_daily_pnl,
    get_overview,
    get_bot_status,
    get_risk_metrics,
    get_module_reports,
)

router = APIRouter()

@router.get("")
@router.get("/")
@router.get("/overview")
def dashboard_overview():
    return get_overview()

@router.get("/equity")
@router.get("/equity/")
def equity_info():
    return get_total_equity()

@router.get("/pnl")
@router.get("/pnl/")
def pnl_info():
    return get_total_pnl()

@router.get("/daily_pnl")
@router.get("/daily_pnl/")
def daily_pnl_info():
    return get_daily_pnl()

@router.get("/status")
@router.get("/status/")
def status_info():
    return get_bot_status()

@router.get("/risk")
@router.get("/risk/")
def risk_metrics():
    return get_risk_metrics()

@router.get("/module_reports")
@router.get("/module_reports/")
def module_reports():
    return get_module_reports()