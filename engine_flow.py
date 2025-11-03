# engine_flow.py — FINAL (Adaptive Trend Mode glue)
from __future__ import annotations
import asyncio, time, traceback
from typing import Dict, Any, Optional, Tuple

from order_manager import OrderManager
from vfi_module import calc_vfi_features, vfi_score
from engine_vote import decide_side as voter_decide_side

try:
    from indicators import IndicatorEngine
except Exception:
    IndicatorEngine = None

class _SafeLogger:
    def info(self, msg: str): print(msg, flush=True)
    def warn(self, msg: str): print("[WARN]", msg, flush=True)
    def error(self, msg: str): print("[ERROR]", msg, flush=True)

_logger = _SafeLogger()
_order_mgr = OrderManager()
_indicator_engine = IndicatorEngine() if IndicatorEngine else None

def _now_ts() -> int: return int(time.time())

def _last(series, default=0.0) -> float:
    try:
        if hasattr(series, "iloc"): return float(series.iloc[-1])
        return float(series)
    except Exception:
        return float(default)

def _ago(series, bars: int, default=0.0) -> float:
    try:
        if hasattr(series, "iloc"):
            idx = -1 - int(bars)
            if abs(idx) <= len(series):
                return float(series.iloc[idx])
            return float(series.iloc[0])
        return float(default)
    except Exception:
        return float(default)

def _age_sec(df) -> Optional[int]:
    try:
        if df is None or len(df) == 0: return None
        ts = int(df["timestamp"].iloc[-1])
        if ts > 10_000_000_000: ts //= 1000
        return max(0, _now_ts() - ts)
    except Exception:
        return None

def _resolve(cfg: dict, *keys, default=None):
    cur = cfg or {}
    for k in keys:
        cur = cur.get(k, {})
    return cur if cur else (default if default is not None else {})

def _as_decision(x) -> tuple[str, float]:
    if isinstance(x, (list, tuple)):
        if len(x) >= 2: return str(x[0]).upper(), float(x[1])
        if len(x) == 1: return str(x[0]).upper(), 0.0
    if isinstance(x, dict):
        return str(x.get("side","NEUTRAL")).upper(), float(x.get("confidence", x.get("score", 0.0)))
    return "NEUTRAL", 0.0

def _calc_vfi(indicators: dict, cfg: dict) -> Tuple[float, Dict[str, float]]:
    enable_vfi = bool(_resolve(cfg, "features").get("enable_vfi", True) or (cfg.get("vfi") is not None))
    if not enable_vfi:
        return 0.0, {"long": 0.0, "short": 0.0}
    m15 = (indicators.get("M15") or {}).get("df")
    if m15 is None or len(getattr(m15, "index", [])) < 30:
        return 0.0, {"long": 0.0, "short": 0.0}
    feats = calc_vfi_features(m15, vwap=(indicators.get("M15") or {}).get("vwap"), atr=(indicators.get("M15") or {}).get("atr"))
    sc_long = vfi_score(feats, "LONG")
    sc_short = vfi_score(feats, "SHORT")
    flow = (sc_long - sc_short) / 100.0
    return float(flow), {"long": float(sc_long), "short": float(sc_short)}

def _m5_trigger_bump(ind: dict, cfg: dict, state: dict, symbol: str) -> float:
    enh = _resolve(cfg, "enhance", "m5_trigger", default={"enabled": False})
    if not enh.get("enabled"): return 0.0
    # chỉ trigger khi M15 "hợp lệ": có biến động và VFI không quá yếu
    m15 = ind.get("M15", {})
    h1  = ind.get("H1", {})
    bbw = _last(m15.get("bbw"), 0.0)
    adx = _last(h1.get("adx"), 0.0)
    if bbw < 0.08 and adx < 14:
        return 0.0
    # tín hiệu M5: giá vượt vwap và EMA21 dốc cùng hướng (đơn giản, chống nhiễu)
    m5 = ind.get("M5", {})
    if not m5:
        return 0.0
    close = m5.get("close"); vwap = m5.get("vwap"); e21 = m5.get("ema21")
    if close is None or vwap is None or e21 is None:
        return 0.0
    anti_gap = int(enh.get("min_gap_secs", 900))
    last_trigger_map = state.setdefault("_m5_last_trigger", {})
    last_ts = last_trigger_map.get(symbol, 0)
    # kiểm tra thời gian nến M5 cuối cùng
    df = m5.get("df")
    if df is None or len(df)==0: return 0.0
    ts_last = int(df["timestamp"].iloc[-1]); 
    if ts_last > 10_000_000_000: ts_last //= 1000
    if ts_last - last_ts < anti_gap:
        return 0.0

    e21_now = _last(e21, 0.0); e21_prev = _ago(e21, 3, e21_now)
    slope_up = (e21_now - e21_prev) > 0
    above_vwap = _last(close, 0.0) > _last(vwap, 0.0)
    below_vwap = _last(close, 0.0) < _last(vwap, 0.0)

    bump = 0.0
    if slope_up and above_vwap:
        bump = 0.03
    elif (not slope_up) and below_vwap:
        bump = -0.03

    if bump != 0.0:
        last_trigger_map[symbol] = ts_last
    return bump

async def run_symbol_cycle(symbol: str, data_feed, cfg: dict, state: dict) -> Dict[str, Any]:
    t0 = time.time()
    result: Dict[str, Any] = {
        "symbol": symbol,
        "status": "INIT",
        "decision": ("FLAT", 0.0),
        "groups": {},
        "vfi_flow": 0.0,
        "vfi_scores": {"long": 0.0, "short": 0.0},
        "latency_sec": 0.0,
    }

    englog = state.get("engine_logger") or _logger
    notifier = state.get("notifier")
    trade_sim = state.get("trade_sim")

    try:
        raw_tf = await data_feed.fetch_all_timeframes(symbol)
        if not raw_tf:
            raise RuntimeError("fetch_all_timeframes returned empty")

        if _indicator_engine is None:
            raise RuntimeError("IndicatorEngine missing")

        indicators = _indicator_engine.compute_all(symbol, raw_tf, cfg)
        if not indicators:
            raise RuntimeError("compute_all returned empty")

        # --- Lag guard trên H1/H4 ---
        enh_lag = _resolve(cfg, "enhance", "lag_guard", default={"enabled": False})
        if enh_lag.get("enabled"):
            h1_age = _age_sec((indicators.get("H1") or {}).get("df"))
            h4_age = _age_sec((indicators.get("H4") or {}).get("df"))
            h1_max = int(enh_lag.get("h1_max_age", 7200))
            h4_max = int(enh_lag.get("h4_max_age", 21600))
            vfi_flow_tmp, vfi_scores_tmp = _calc_vfi(indicators, cfg)
            skip_if_flow = float(enh_lag.get("skip_if_vfi_flow_over", 0.2))
            if ((h1_age and h1_age > h1_max) or (h4_age and h4_age > h4_max)) and abs(vfi_flow_tmp) < skip_if_flow:
                if enh_lag.get("neutral_if_true", True):
                    # trung lập hóa quyết định vì dữ liệu cũ
                    result.update({
                        "status":"LAG_GUARD",
                        "groups":{},
                        "vfi_flow": vfi_flow_tmp,
                        "vfi_scores": vfi_scores_tmp,
                        "decision": ("FLAT", 0.0)
                    })
                    return result

        # --- VFI ---
        vfi_flow, vfi_scores = _calc_vfi(indicators, cfg)

        # --- nhóm gốc (nếu chưa có tally_groups chuyên sâu) ---
        groups = {
            "flow": vfi_flow,
            "trend": 0.0,
            "momentum": 0.0,
            "mean": 0.0
        }

        # --- Early bump từ M5 trigger (nếu bật) ---
        m5_bump = _m5_trigger_bump(indicators, cfg, state, symbol)
        if m5_bump:
            groups["momentum"] += m5_bump

        # --- Vote ---
        ctx_vote = {
            "indicators": indicators,
            "config": cfg,
            "group_scores": groups,
            "vfi_scores": vfi_scores,
        }
        vote = voter_decide_side(ctx_vote) or {"side": "NEUTRAL", "score": 0.0}
        side, conf = _as_decision((vote.get("side","NEUTRAL"), vote.get("score",0.0)))

        result.update({
            "status": "OK",
            "groups": groups,
            "vfi_flow": vfi_flow,
            "vfi_scores": vfi_scores,
            "decision": (side, conf)
        })

        # --- log snapshot chi tiết (nếu có logger) ---
        if englog and hasattr(englog, "log_vote_snapshot"):
            englog.log_vote_snapshot({
                "symbol": symbol,
                "regime": "",  # (để ngỏ, sẽ điền khi có RegimeDetector)
                "trend": groups.get("trend",0.0),
                "momentum": groups.get("momentum",0.0),
                "mean": groups.get("mean",0.0),
                "flow": groups.get("flow",0.0),
                "score": conf,
                "side": side,
                "details": vote.get("details", {})
            })

        # --- handle trades ---
        if side in ("LONG", "SHORT"):
            _order_mgr.open_if_ok(
                {"symbol": symbol, "cfg": cfg, "indicators": indicators, "trade_sim": trade_sim, "notifier": notifier, "logger": englog},
                side,
            )
        _order_mgr.manage({"symbol": symbol, "cfg": cfg, "indicators": indicators, "trade_sim": trade_sim, "notifier": notifier, "logger": englog})

    except Exception as e:
        englog.error(f"[ENGINE_FLOW][{symbol}] {e}\n{traceback.format_exc()}")
        result["status"] = "ERROR"
    finally:
        result["latency_sec"] = round(time.time() - t0, 3)
        return result

async def engine_loop(symbols: list[str], data_feed, cfg: dict, state: dict):
    tasks = [run_symbol_cycle(sym, data_feed, cfg, state) for sym in symbols]
    return await asyncio.gather(*tasks, return_exceptions=True)
