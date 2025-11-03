import math
from typing import Tuple

def _round_step(x: float, step: float) -> float:
    if step <= 0: return x
    return round(math.floor(x / step) * step, 10)

def compute_size(entry: float, sl: float, balance_quote: float, risk_pct: float,
                 price_step: float=0.0, qty_step: float=0.0, min_notional: float=5.0) -> Tuple[float,float]:
    entry=float(entry); sl=float(sl); risk_pct=float(risk_pct); balance_quote=float(balance_quote)
    risk_amt=max(0.0, balance_quote * max(0.0, risk_pct))
    R=abs(entry - sl)
    if R <= 0 or risk_amt <= 0: return 0.0, 0.0
    qty=risk_amt / R
    qty=_round_step(qty, qty_step) if qty_step>0 else qty
    notional=qty * entry
    if notional < min_notional:
        target_qty = min_notional / max(1e-12, entry)
        qty=_round_step(target_qty, qty_step) if qty_step>0 else target_qty
        notional=qty*entry
    return float(qty), float(notional)
