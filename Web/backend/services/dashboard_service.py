import json
import csv
from datetime import datetime
from collections import defaultdict
from services.constants import TRADE_LOG, SIGNALS_LOG, TRADE_STATE, CONFIG, ALERTS_LOG

TRADE_LOG = "../../trades_log.csv"
SIGNALS_LOG = "../../signals_log.csv"
TRADE_STATE = "../../trade_state.json"
CONFIG = "../../config.json"

def safe_float(val, default=0.0):
    try:
        if val in (None, "", "None"):
            return default
        return float(val)
    except Exception:
        return default

def safe_load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def safe_load_csv(path):
    result = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for k, v in row.items():
                    if v == "None":
                        row[k] = ""
                result.append(row)
    except Exception:
        pass
    return result

def get_total_equity():
    state = safe_load_json(TRADE_STATE)
    if state and "equity" in state:
        return {"equity": safe_float(state.get("equity", 0))}
    config = safe_load_json(CONFIG)
    return {"equity": safe_float(config.get("initial_equity", 0))}

def get_total_pnl():
    trades = safe_load_csv(TRADE_LOG)
    pnl = 0.0
    for t in trades:
        pnl += safe_float(t.get("pnl", 0))
    return {"total_pnl": pnl}

def get_daily_pnl():
    trades = safe_load_csv(TRADE_LOG)
    daily = defaultdict(float)
    for t in trades:
        dt = t.get("close_time") or t.get("timestamp") or ""
        date = dt.split(" ")[0] if dt else "unknown"
        daily[date] += safe_float(t.get("pnl", 0))
    return [{"date": d, "pnl": daily[d]} for d in sorted(daily.keys())]

def get_bot_status():
    state = safe_load_json(TRADE_STATE)
    if not state:
        return {"status": "unknown", "detail": "No state file"}
    return {
        "status": state.get("status", "unknown"),
        "last_action": state.get("last_action", ""),
        "open_trades": state.get("open_trades", []),
        "update_time": state.get("update_time", "")
    }

def get_risk_metrics():
    trades = safe_load_csv(TRADE_LOG)
    total = len(trades)
    win = sum(1 for t in trades if safe_float(t.get("pnl", 0)) > 0)
    winrate = (win / total * 100) if total else 0
    eq = 0
    eqs = []
    for t in trades:
        eq += safe_float(t.get("pnl", 0))
        eqs.append(eq)
    drawdown = 0
    peak = 0
    for x in eqs:
        if x > peak:
            peak = x
        if peak - x > drawdown:
            drawdown = peak - x
    return {
        "winrate": winrate,
        "max_drawdown": drawdown,
        "trade_count": total
    }

def get_module_reports():
    signals = safe_load_csv(SIGNALS_LOG)
    trades = safe_load_csv(TRADE_LOG)
    module = {
        "signals_count": len(signals),
        "total_trades": len(trades),
        "open_trades": [t for t in trades if t.get("status") == "open"],
        "closed_trades": [t for t in trades if t.get("status") == "closed"],
    }
    return module

def get_overview():
    eq = get_total_equity()
    pnl = get_total_pnl()
    daily = get_daily_pnl()
    state = get_bot_status()
    risk = get_risk_metrics()
    overview = {
        "equity": eq.get("equity", 0),
        "total_pnl": pnl.get("total_pnl", 0),
        "last_daily_pnl": daily[-1] if isinstance(daily, list) and daily else {},
        "status": state,
        "risk_metrics": risk,
    }
    overview["balance"] = overview["equity"]
    overview["pnl_today"] = overview.get("last_daily_pnl", {}).get("pnl", 0)
    overview["orders_open"] = len(state.get("open_trades", [])) if isinstance(state, dict) else 0
    overview["orders_win_rate"] = risk.get("winrate", 0) / 100 if risk.get("winrate") is not None else 0
    return overview