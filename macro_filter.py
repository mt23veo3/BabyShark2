from __future__ import annotations
from typing import Dict, Any

def detect_regime(ind: Dict[str, Any]) -> str:
    h1 = ind.get("H1", {}) or {}
    try:
        adx = float(h1.get("adx", 0))
        bbw = float(h1.get("bbw_pctl", 0.5))
        atr_s = float(h1.get("atr_slope", 0))
        vol = float(h1.get("vol", 0)); vma = float(h1.get("vol_ma50", 1) or 1)
        if bbw < 0.15 and vol < 0.8 * vma:
            return "COMPRESSION"
        if bbw > 0.85 and (vol > 1.5 * vma or atr_s > 0):
            return "EXPLOSIVE"
        if 20 <= adx <= 25 or (0.3 <= bbw <= 0.6):
            return "TRANSITION"
        if adx > 25:
            return "TREND"
        return "SIDEWAY"
    except Exception:
        return "SIDEWAY"

def macro_bias(ind: Dict[str, Any]) -> str:
    h1, h4 = ind.get("H1", {}) or {}, ind.get("H4", {}) or {}
    try:
        h1_up = float(h1.get("close",0)) > float(h1.get("ema200",0))
        h4_up = float(h4.get("close",0)) > float(h4.get("ema200",0))
        vfi_up = float(h1.get("vfi",0)) > 0
        if h1_up and h4_up and vfi_up: return "LONG"
        if (not h1_up) and (not h4_up) and (float(h1.get("vfi",0)) < 0): return "SHORT"
        return "FLAT"
    except Exception:
        return "FLAT"

def classify(ind: Dict[str, Any]) -> Dict[str, str]:
    return {"regime": detect_regime(ind), "macro_bias": macro_bias(ind)}
