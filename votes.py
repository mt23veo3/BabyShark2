
from __future__ import annotations
from typing import Dict, Any

def _sgn(pos: bool, neg: bool) -> float:
    if pos and not neg: return 1.0
    if neg and not pos: return -1.0
    return 0.0

def vote_trend(ind: Dict[str, Any]) -> float:
    s = 0.0
    h1 = ind.get("H1", {}) or {}
    try:
        s += _sgn(h1.get("ema50",0) > h1.get("ema200",0), h1.get("ema50",0) < h1.get("ema200",0)) * 0.6
        s += _sgn(h1.get("ema9",0) > h1.get("ema21",0), h1.get("ema9",0) < h1.get("ema21",0)) * 0.4
    except Exception:
        pass
    return max(-1.0, min(1.0, s))

def vote_momentum(ind: Dict[str, Any]) -> float:
    s = 0.0
    m15 = ind.get("M15", {}) or {}
    try:
        s += _sgn(m15.get("rsi",50) > 55, m15.get("rsi",50) < 45) * 0.5
        s += _sgn(m15.get("roc",0) > 0,  m15.get("roc",0) < 0)   * 0.3
        s += _sgn(m15.get("macd_hist",0) > 0, m15.get("macd_hist",0) < 0) * 0.2
    except Exception:
        pass
    return max(-1.0, min(1.0, s))

def vote_volume(ind: Dict[str, Any]) -> float:
    s = 0.0
    h1, m15 = ind.get("H1", {}) or {}, ind.get("M15", {}) or {}
    try:
        s += _sgn(h1.get("obv_slope",0) > 0, h1.get("obv_slope",0) < 0) * 0.6
        vol = float(m15.get("vol", 0.0) or 0.0)
        vma = float(m15.get("vol_ma20", 0.0) or 0.0)
        if vma > 0.0:
            s += _sgn(vol > 1.2 * vma, vol < 0.8 * vma) * 0.4
        # if vma == 0: lack data -> no penalty
    except Exception:
        pass
    return max(-1.0, min(1.0, s))

def vote_volatility(ind: Dict[str, Any]) -> float:
    s = 0.0
    h1 = ind.get("H1", {}) or {}
    try:
        p = float(h1.get("bbw_pctl", 0.5) or 0.5)
        s += _sgn(p >= 0.7, p <= 0.3) * 1.0
    except Exception:
        pass
    return max(-1.0, min(1.0, s))

def vote_mean(ind: Dict[str, Any]) -> float:
    s = 0.0
    m15 = ind.get("M15", {}) or {}
    try:
        price = float(m15.get("close",0.0) or 0.0)
        vwap  = float(m15.get("vwap", price) or price)
        s += _sgn(price > vwap, price < vwap) * 1.0
    except Exception:
        pass
    return max(-1.0, min(1.0, s))

def tally_groups(ind: Dict[str, Dict[str, float]], weights: Dict[str, float]) -> Dict[str, Any]:
    groups = {
        "trend":      vote_trend(ind),
        "momentum":   vote_momentum(ind),
        "volume":     vote_volume(ind),
        "volatility": vote_volatility(ind),
        "mean":       vote_mean(ind),
    }

    score_long  = 0.0
    score_short = 0.0
    for k, v in groups.items():
        try:
            w = float(weights.get(k, 1.0) or 1.0)
        except Exception:
            w = 1.0
        if v > 0: score_long  += v * w
        if v < 0: score_short += (-v) * w

    return {"groups": groups, "score_long": score_long, "score_short": score_short}
