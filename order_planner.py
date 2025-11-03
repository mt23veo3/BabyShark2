from typing import Dict, Tuple
from position_sizer import compute_size


def _get_account_balance_quote(cfg: Dict) -> float:
    """
    Lấy số dư quote cho chế độ paper trading (hoặc live nếu có).
    """
    trading = cfg.get("trading") or {}
    return float(trading.get("paper_balance_quote", 10000.0))


def plan_probe_and_topup(side: str, ohlcv_m15, indicators_m15: Dict, cfg: Dict) -> Dict:
    """
    GIỮ NGUYÊN HÀM CŨ (backward-compatible):
    - Entry: lấy giá close hiện tại.
    - SL = sl_atr_mult * ATR (theo tight_mode hoặc mặc định).
    - TP theo RR target trong tight_mode.
    - Tính size qua compute_size.
    """
    entry = float(ohlcv_m15["close"].iloc[-1])

    atr_series = indicators_m15.get("atr")
    if hasattr(atr_series, "iloc"):
        atr = float(atr_series.iloc[-1])
    else:
        atr = entry * 0.01  # fallback an toàn

    tight = cfg.get("tight_mode") or {}
    sl_mult = float(tight.get("sl_atr_mult", 1.2))
    rr = float(tight.get("rr_target", 2.0))

    if side == "LONG":
        sl = entry - sl_mult * atr
        r_value = entry - sl
        tp = entry + rr * r_value
    else:
        sl = entry + sl_mult * atr
        r_value = sl - entry
        tp = entry - rr * r_value

    bal_q = _get_account_balance_quote(cfg)
    risk = cfg.get("risk") or {}
    qty_full, notional = compute_size(
        entry=entry,
        sl=sl,
        balance_quote=bal_q,
        risk_pct=float(risk.get("per_trade_risk_pct", 0.01)),
        price_step=float(risk.get("price_step", 0.0)),
        qty_step=float(risk.get("qty_step", 0.0)),
        min_notional=float(risk.get("min_notional", 5.0)),
    )
    return {
        "entry_price": round(entry, 6),
        "sl": round(sl, 6),
        "tp": round(tp, 6),
        "r_value": round(r_value, 6),
        "size_full": float(qty_full),
        "notional_full": round(notional, 4),
    }


# -------------------------- MỚI: Transition/Microtrend Scalp -------------------------- #
def plan_transition_scalp(entry: float, direction: str, atr: float, cfg: Dict) -> Tuple[float, float]:
    """
    SL/TP cho microtrend scalp (transition):
      - SL = sl_atr * ATR  (mặc định 1.0 ATR)
      - TP = entry ± (tp_r * R) (mặc định 1.2R)
    Trả về (sl, tp)
    """
    ex = (cfg.get("exit") or {}).get("transition", {}) or {}
    sl_atr = float(ex.get("sl_atr", 1.0))
    tp_r = float(ex.get("tp_r", 1.2))

    if direction == "LONG":
        sl = entry - sl_atr * atr
        R = entry - sl
        tp = entry + tp_r * max(R, 1e-9)
    else:
        sl = entry + sl_atr * atr
        R = sl - entry
        tp = entry - tp_r * max(R, 1e-9)

    return round(sl, 6), round(tp, 6)
