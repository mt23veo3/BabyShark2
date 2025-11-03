# transition_strategy.py
from __future__ import annotations
from typing import Dict, Any, Optional
import time

from trade_hooks import (
    should_open_early_probe, should_promote_probe,
    time_based_probe_exit, absorption_pause_guard,
    manage_trailing_and_partial, _notify_open_trade
)

def _get_last(d: Dict[str, Any], col: str, default: float = 0.0) -> float:
    try:
        s = d.get(col)
        if hasattr(s, "iloc"): return float(s.iloc[-1])
        if isinstance(s, (list, tuple)) and s: return float(s[-1])
        return float(s or default)
    except Exception:
        return float(default)

def _open_trade_safe(exec_engine, symbol: str, direction: str, entry: float, sl: float, tp: float,
                     size_quote: Optional[float], setup: str, notifier, reason: str = "") -> Optional[Dict[str, Any]]:
    trade = None
    try:
        sim = getattr(exec_engine, "simulator", None)
        if sim and hasattr(sim, "open_trade"):
            trade = sim.open_trade(symbol, direction, entry, sl, tp, size_quote=size_quote)
            if isinstance(trade, dict):
                trade["setup"] = setup
                trade["reason"] = reason
                trade["created_ts"] = int(time.time())
    except Exception:
        trade = None

    try:
        if trade is not None and notifier is not None:
            _notify_open_trade(trade, notifier)
    except Exception:
        pass

    return trade

def process_transition_symbol(*args, **kwargs):
    """
    process_transition_symbol(symbol, frames, indicators, votes, cfg, notifier, state, exec_engine, now_epoch)

    Nâng cấp:
      - Dùng ctx["mode"] (SCALPER/SWING) để chỉnh SL/TP/trailing/time-based.
      - Dùng ctx["macro_regime"]:
          * CONFLICT: chỉ PROBE, không promote.
          * TREND_ALIGN: promote nhanh hơn (nới điều kiện).
      - Vẫn giữ absorption_pause_guard.
    """
    if args and not kwargs:
        (symbol, frames, indicators, votes, cfg, notifier, state, exec_engine, now_epoch) = (list(args) + [None] * 9)[:9]
    else:
        symbol      = kwargs.get("symbol")
        frames      = kwargs.get("frames") or {}
        indicators  = kwargs.get("indicators") or {}
        votes       = kwargs.get("votes") or {}
        cfg         = kwargs.get("cfg") or {}
        notifier    = kwargs.get("notifier")
        state       = kwargs.get("state")
        exec_engine = kwargs.get("exec_engine")
        now_epoch   = kwargs.get("now_epoch", int(time.time()))

    ind_m15 = indicators.get("M15") or {}
    price = _get_last(ind_m15, "close")
    vwap  = _get_last(ind_m15, "vwap")
    atr   = _get_last(ind_m15, "atr")

    # Context
    ctx = votes.get("_ctx", {}) if isinstance(votes, dict) else {}
    side_m15   = (ctx.get("side_m15") or votes.get("side_m15") or "").upper()
    m15_h1_ok  = bool(ctx.get("m15_h1_ok", votes.get("m15_h1_ok", False)))
    score_ok   = bool(ctx.get("score_ok", votes.get("score_ok", False)))
    regime     = (ctx.get("regime") or votes.get("regime") or "WEAK").upper()
    anti_ok    = bool(ctx.get("anti_chase_ok", True))
    snapshot_ok= bool(ctx.get("m5_ok", votes.get("m5_ok", False)))
    mode       = (ctx.get("mode") or "SCALPER").upper()
    macro      = (ctx.get("macro_regime") or "SIDEWAY_MACRO").upper()

    # Wick absorption pause (giữ nguyên)
    try:
        wick_guard_cfg = (cfg.get("vfi", {}).get("wick_absorb_guard", {}) or {})
        wick_on   = bool(wick_guard_cfg.get("enabled", True))
        wick_thr  = float(wick_guard_cfg.get("ratio", 1.8))
        cool_down = int(wick_guard_cfg.get("cool_down_sec", 60))
        if wick_on and absorption_pause_guard(symbol, ind_m15, wick_absorb_thresh=wick_thr, cool_down_sec=cool_down):
            return
    except Exception:
        pass

    # Tham số theo mode
    if mode == "SWING":
        probe_sl_mult = float(cfg.get("engine", {}).get("early_probe", {}).get("sl_atr_mult", 1.4))
        probe_tp_mult = float(cfg.get("engine", {}).get("early_probe", {}).get("tp_atr_mult", 1.2)) * 1.15
        trailing_mult = min(1.0, float(cfg.get("engine", {}).get("manage", {}).get("trailing_atr_mult", 1.2)))
        tbe_minutes   = int(cfg.get("engine", {}).get("time_based_probe_exit", {}).get("max_minutes", 20)) * 2
    else:  # SCALPER
        probe_sl_mult = float(cfg.get("engine", {}).get("early_probe", {}).get("sl_atr_mult", 1.4)) * 1.0
        probe_tp_mult = float(cfg.get("engine", {}).get("early_probe", {}).get("tp_atr_mult", 1.2))
        trailing_mult = max(1.2, float(cfg.get("engine", {}).get("manage", {}).get("trailing_atr_mult", 1.2)))
        tbe_minutes   = max(8, int(cfg.get("engine", {}).get("time_based_probe_exit", {}).get("max_minutes", 20)) // 2)

    # ========= EARLY PROBE =========
    try:
        early_cfg = (cfg.get("engine", {}).get("early_probe", {}) or {})
        if bool(early_cfg.get("enabled", True)):
            if should_open_early_probe(side_m15=side_m15, anti_chase_ok=anti_ok, snapshot_ok=snapshot_ok):
                sl_mult = probe_sl_mult * (1.1 if macro == "CONFLICT" else 1.0)
                tp_mult = probe_tp_mult * (0.9 if macro == "CONFLICT" else 1.0)

                if side_m15 == "LONG":
                    sl = price - sl_mult * atr
                    tp = price + tp_mult * atr
                else:
                    sl = price + sl_mult * atr
                    tp = price - tp_mult * atr

                size_quote = float(early_cfg.get("probe_size_quote", cfg.get("transition_probe_size_quote", cfg.get("probe_size_quote", 0))))
                _open_trade_safe(exec_engine, symbol, side_m15, price, sl, tp, size_quote,
                                 setup="TRANSITION", notifier=notifier, reason=f"early_probe(mode={mode},macro={macro})")
    except Exception:
        pass

    # ========= PROMOTE PROBE → FULL =========
    try:
        prom_cfg = (cfg.get("engine", {}).get("promote", {}) or {})
        allow_promote = (macro != "CONFLICT")  # chặn promote khi macro conflict
        promote_ready = should_promote_probe(
            m15_h1_ok = (m15_h1_ok or (macro=="TREND_ALIGN" and regime in ("NORMAL","STRONG"))),
            score_ok  = score_ok,
            regime_ok = (regime in ("NORMAL","STRONG"))
        )
        if allow_promote and promote_ready:
            sim = getattr(exec_engine, "simulator", None)
            active = None
            if sim and hasattr(sim, "find_open_probe"):
                try: active = sim.find_open_probe(symbol, side_m15)
                except Exception: active = None
            if active is None and sim and hasattr(sim, "get_open_trades"):
                try:
                    opens = sim.get_open_trades(symbol) or []
                    for t in reversed(opens):
                        if t.get("direction")==side_m15 and t.get("size_type")=="PROBE":
                            active = t; break
                except Exception: active = None
            if active:
                sl_mult = float(prom_cfg.get("sl_atr_mult", cfg.get("transition_atr_sl_mult", 1.6)))
                tp_mult = float(prom_cfg.get("tp_atr_mult", 1.8))
                if mode == "SWING": tp_mult *= 1.05
                if side_m15=="LONG":
                    new_sl = price - sl_mult * atr; new_tp = price + tp_mult * atr
                else:
                    new_sl = price + sl_mult * atr; new_tp = price - tp_mult * atr

                add_quote = float(prom_cfg.get("promote_add_size_quote", cfg.get("transition_promote_add_size_quote", cfg.get("promote_add_size_quote", 0))))
                try:
                    if add_quote>0 and hasattr(sim,"add_size"): sim.add_size(active, add_quote)
                except Exception: pass
                try:
                    if hasattr(sim,"modify_sl_tp"): sim.modify_sl_tp(active, new_sl, new_tp)
                except Exception: pass
    except Exception:
        pass

    # ========= TIME-BASED EXIT (PROBE) =========
    try:
        tb_cfg = (cfg.get("engine", {}).get("time_based_probe_exit", {}) or {})
        if bool(tb_cfg.get("enabled", True)):
            sim = getattr(exec_engine, "simulator", None)
            if sim and hasattr(sim, "get_open_trades"):
                opens = sim.get_open_trades(symbol) or []
                for t in list(opens):
                    if t.get("size_type") == "PROBE" and t.get("direction") in ("LONG","SHORT"):
                        if time_based_probe_exit(t, max_minutes=tbe_minutes, now_ts=now_epoch):
                            try:
                                if hasattr(sim, "close_trade"): sim.close_trade(t, reason=f"time_based_exit(mode={mode})")
                            except Exception: pass
    except Exception:
        pass

    # ========= QUẢN TRỊ: partial TP + trailing =========
    try:
        mg_cfg = (cfg.get("engine", {}).get("manage", {}) or {})
        if bool(mg_cfg.get("enabled", True)):
            sim = getattr(exec_engine, "simulator", None)
            if sim and hasattr(sim, "get_open_trades"):
                opens = sim.get_open_trades(symbol) or []
                for t in list(opens):
                    if t.get("direction") not in ("LONG","SHORT"): continue
                    res = manage_trailing_and_partial(t, price, atr=atr,
                                                      enable_trailing=bool(mg_cfg.get("trailing_enabled", True)),
                                                      trailing_mult=trailing_mult)
                    new_sl = res.get("new_sl")
                    if new_sl is not None and hasattr(sim, "modify_sl"):
                        try: sim.modify_sl(t, float(new_sl))
                        except Exception: pass
                    tp_level = int(res.get("tp_level", 0))
                    if tp_level > 0 and hasattr(sim, "partial_close"):
                        try:
                            pct = 0.35 if tp_level == 1 else 0.40
                            if mode == "SWING": pct = 0.25 if tp_level == 1 else 0.30
                            sim.partial_close(t, pct, reason=f"partial_tp{tp_level}(mode={mode})")
                        except Exception: pass
    except Exception:
        pass

    return
