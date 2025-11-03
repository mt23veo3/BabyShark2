# sideway_strategy.py
from __future__ import annotations
from typing import Dict, Any, Optional
import csv
from pathlib import Path
import time

from trade_hooks import manage_trailing_and_partial, _notify_open_trade

def _append_entries_reason_csv(row: dict):
    path = Path("entries_reasons.csv")
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "ts","symbol","setup","direction","entry","sl","tp","atr",
            "rsi","bbw_norm","dist_up","dist_lo","bb_lower","bb_upper","reason"
        ])
        if new_file: w.writeheader()
        w.writerow(row)

def _get_last(d: Dict[str, Any], col: str, default: float = 0.0) -> float:
    try:
        s = d.get(col)
        if hasattr(s, "iloc"): return float(s.iloc[-1])
        if isinstance(s, (list, tuple)) and s: return float(s[-1])
        return float(s or default)
    except Exception:
        return float(default)

def process_sideway_symbol(*args, **kwargs):
    """
    process_sideway_symbol(symbol, frames, indicators, votes, cfg, notifier, state, exec_engine, now_epoch)
    - Giữ nguyên logic sideway: mean-revert theo band/RSI.
    - Bổ sung: log CSV khi vào lệnh + quản trị trailing/partial.
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
    atr   = _get_last(ind_m15, "atr")

    # ======= (A) VÀO LỆNH SIDEWAY (placeholder mean-revert cơ bản) =======
    # NOTE: nếu dự án của anh đã có bộ điều kiện sideway riêng, đoạn dưới sẽ được thay bằng gọi hàm cũ.
    try:
        # Điều kiện demo: nếu có BB/RSI thì dùng, nếu không thì bỏ qua entry.
        rsi = _get_last(ind_m15, "rsi")
        bb_lo = _get_last(ind_m15, "bb_lower")
        bb_up = _get_last(ind_m15, "bb_upper")

        direction = None
        if rsi and bb_lo and price <= bb_lo:
            direction = "LONG"
        elif rsi and bb_up and price >= bb_up:
            direction = "SHORT"

        if direction in ("LONG","SHORT"):
            sl_mult = float(cfg.get("atr_sl_mult", 1.2))
            tp_mult = 1.0  # sideway TP ngắn hơn trend
            if direction == "LONG":
                sl = price - sl_mult * atr
                tp = price + tp_mult * atr
            else:
                sl = price + sl_mult * atr
                tp = price - tp_mult * atr

            # mở lệnh
            trade = None
            sim = getattr(exec_engine, "simulator", None)
            if sim and hasattr(sim, "open_trade"):
                trade = sim.open_trade(symbol, direction, price, sl, tp, size_quote=float(cfg.get("probe_size_quote", 10)))
                if isinstance(trade, dict):
                    trade["sideway"] = True
                    trade["setup"] = "SIDEWAY"
                    trade["reason"] = "sideway_entry"
                    trade["created_ts"] = int(time.time())
            try:
                if trade is not None and notifier is not None:
                    _notify_open_trade(trade, notifier)
            except Exception:
                pass

            # CSV lý do vào lệnh
            try:
                bbw_norm = _get_last(ind_m15, "bbw_norm")
                dist_up  = abs(price - bb_up) if bb_up else None
                dist_lo  = abs(price - bb_lo) if bb_lo else None
                _append_entries_reason_csv({
                    "ts": int(now_epoch),
                    "symbol": symbol,
                    "setup": "SIDEWAY",
                    "direction": direction,
                    "entry": price,
                    "sl": sl,
                    "tp": tp,
                    "atr": atr,
                    "rsi": rsi,
                    "bbw_norm": bbw_norm,
                    "dist_up": dist_up,
                    "dist_lo": dist_lo,
                    "bb_lower": bb_lo,
                    "bb_upper": bb_up,
                    "reason": "sideway_entry"
                })
            except Exception:
                pass
    except Exception:
        pass

    # ======= (B) QUẢN TRỊ: trailing/partial =======
    try:
        sim = getattr(exec_engine, "simulator", None)
        if sim and hasattr(sim, "get_open_trades"):
            opens = sim.get_open_trades(symbol) or []
            for t in list(opens):
                if not t.get("sideway"):  # chỉ áp dụng cho lệnh sideway
                    continue
                res = manage_trailing_and_partial(t, price, atr=atr,
                                                  enable_trailing=True,
                                                  trailing_mult=1.0)  # sideway trailing ngắn hơn
                new_sl = res.get("new_sl")
                if new_sl is not None and hasattr(sim, "modify_sl"):
                    try: sim.modify_sl(t, float(new_sl))
                    except Exception: pass
                tp_level = int(res.get("tp_level", 0))
                if tp_level > 0 and hasattr(sim, "partial_close"):
                    try:
                        pct = 0.5 if tp_level == 1 else 0.5
                        sim.partial_close(t, pct, reason=f"sideway_partial_tp{tp_level}")
                    except Exception: pass
    except Exception:
        pass

    return
