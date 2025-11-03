from typing import Dict, Tuple
import pandas as pd
from .types import GateResult, Side
from ..indicators.ta import ema, atr, adx, supertrend, vwap, range_filter_direction, rsi, slope

def _heavy_direction(ema200_up: bool, st_dir: int, rf_dir: int, side: Side) -> int:
    score = 0
    if side == "long":
        score += 1 if ema200_up else 0
        score += 1 if st_dir == 1 else 0
        score += 1 if rf_dir == 1 else 0
    else:
        score += 1 if (not ema200_up) else 0
        score += 1 if st_dir == -1 else 0
        score += 1 if rf_dir == -1 else 0
    return score

def compute_h1_gate(h1_df: pd.DataFrame, side: Side, cfg: Dict) -> Tuple[bool, Dict]:
    h1 = h1_df.copy()
    ema200 = ema(h1["close"], 200)
    ema200_up = ema200.iloc[-1] > ema200.iloc[-2]
    st = supertrend(h1["high"], h1["low"], h1["close"], cfg["supertrend"]["atr_period"], cfg["supertrend"]["multiplier"]).iloc[-1]
    rf = range_filter_direction(h1["close"], h1["high"], h1["low"], cfg["range_filter"]["length"], cfg["range_filter"]["atr_mult"]).iloc[-1]
    adx_val = adx(h1["high"], h1["low"], h1["close"], cfg["adx_h1_period"]).iloc[-1]
    heavy_hits = _heavy_direction(ema200_up, st, rf, side)
    ok = (adx_val >= cfg["adx_h1_threshold"]) and (heavy_hits >= cfg["heavy_required_h1"])
    return ok, {
        "adx": float(adx_val),
        "ema200_up": bool(ema200_up),
        "st_dir": int(st),
        "rf_dir": int(rf),
        "heavy_hits": int(heavy_hits)
    }

def compute_m15_features(m15_df: pd.DataFrame, h1_ctx: Dict, side: Side, cfg: Dict) -> Dict:
    m15 = m15_df.copy()
    ema20 = ema(m15["close"], 20)
    ema50 = ema(m15["close"], 50)
    ema200 = ema(m15["close"], 200)
    st = supertrend(m15["high"], m15["low"], m15["close"], cfg["supertrend"]["atr_period"], cfg["supertrend"]["multiplier"])
    rf = range_filter_direction(m15["close"], m15["high"], m15["low"], cfg["range_filter"]["length"], cfg["range_filter"]["atr_mult"])
    atrv = atr(m15["high"], m15["low"], m15["close"], cfg["atr_period"])
    rsi_m15 = rsi(m15["close"], cfg["rsi_m15_period"])
    vwap_m15 = vwap(m15["close"], m15.get("volume", pd.Series(index=m15.index, data=0.0)), cfg.get("vwap_anchor", "daily_utc"))

    close = m15["close"]
    high = m15["high"]
    low = m15["low"]

    ema200_up = ema200.iloc[-1] > ema200.iloc[-2]
    ema50_up = ema50.iloc[-1] > ema50.iloc[-2]
    ema20_up = ema20.iloc[-1] > ema20.iloc[-2]

    st_dir = st.iloc[-1]
    rf_dir = rf.iloc[-1]

    heavy_hits_m15 = _heavy_direction(ema200_up, st_dir, rf_dir, side)

    curr = len(m15) - 1
    c0, c1 = close.iloc[-1], close.iloc[-2]
    h0, h1v = high.iloc[-1], high.iloc[-2]
    l0, l1v = low.iloc[-1], low.iloc[-2]
    rsi0, rsi1 = rsi_m15.iloc[-1], rsi_m15.iloc[-2]
    vwap0 = vwap_m15.iloc[-1]
    atr0 = atrv.iloc[-1]

    # Build 18-point score (long side)
    score = 0
    reasons = []

    def add(flag: bool, key: str):
        nonlocal score, reasons
        if flag:
            score += 1
            reasons.append(key)

    if side == "long":
        add(c0 > ema200.iloc[-1], "c>ema200")
        add(ema200_up, "ema200_up")
        add(st_dir == 1, "st_long")
        add(rf_dir == 1, "rf_long")
        add(c0 > ema50.iloc[-1], "c>ema50")
        add(ema50_up, "ema50_up")
        add(c0 > ema20.iloc[-1], "c>ema20")
        add(ema20_up, "ema20_up")
        add(c0 > vwap0, "c>vwap")
        add(abs(c0 - vwap0) <= cfg["anti_chase_atr_mult"] * atr0, "dist_vwap_ok")
        add(c0 > c1, "close_rising")
        add(l0 >= l1v, "hl")
        add(h0 >= h1v, "hh")
        add(rsi0 >= 55, "rsi>=55")
        add(rsi0 >= rsi1, "rsi_rising")
        # H1 context contributions
        add(h1_ctx.get("ema200_up", False), "h1_ema200_up")
        add(h1_ctx.get("st_dir", -1) == 1, "h1_st_long")
        add(h1_ctx.get("rf_dir", -1) == 1, "h1_rf_long")
    else:
        add(c0 < ema200.iloc[-1], "c<ema200")
        add(not ema200_up, "ema200_dn")
        add(st_dir == -1, "st_short")
        add(rf_dir == -1, "rf_short")
        add(c0 < ema50.iloc[-1], "c<ema50")
        add(not ema50_up, "ema50_dn")
        add(c0 < ema20.iloc[-1], "c<ema20")
        add(not ema20_up, "ema20_dn")
        add(c0 < vwap0, "c<vwap")
        add(abs(c0 - vwap0) <= cfg["anti_chase_atr_mult"] * atr0, "dist_vwap_ok")
        add(c0 < c1, "close_falling")
        add(l0 <= l1v, "lh")
        add(h0 <= h1v, "ll")
        add(rsi0 <= 45, "rsi<=45")
        add(rsi0 <= rsi1, "rsi_falling")
        add(not h1_ctx.get("ema200_up", True), "h1_ema200_dn")
        add(h1_ctx.get("st_dir", 1) == -1, "h1_st_short")
        add(h1_ctx.get("rf_dir", 1) == -1, "h1_rf_short")

    features = {
        "score": int(score),
        "reasons": reasons,
        "heavy_hits_m15": int(heavy_hits_m15),
        "anti_chase_ok": bool(abs(c0 - vwap0) <= cfg["anti_chase_atr_mult"] * atr0)
    }
    return features

def compute_gates(h1_df: pd.DataFrame, m15_df: pd.DataFrame, symbol: str, side: Side, cfg: Dict) -> GateResult:
    h1_ok, h1_ctx = compute_h1_gate(h1_df, side, cfg)
    m15_feats = compute_m15_features(m15_df, h1_ctx, side, cfg)

    m15_ok = m15_feats["score"] >= cfg["score_threshold_m15"]
    heavy_ok = m15_feats["heavy_hits_m15"] >= cfg["heavy_required_m15"]
    anti_chase_ok = m15_feats["anti_chase_ok"]

    reasons = []
    if h1_ok: reasons.append("h1_ok")
    if m15_ok: reasons.append("m15_score_ok")
    if heavy_ok: reasons.append("heavy_m15_ok")
    if anti_chase_ok: reasons.append("anti_chase_ok")

    return GateResult(
        symbol=symbol,
        timeframe_m15_ts=int(m15_df.index[-1].value // 1_000_000),  # ns->ms
        side=side,
        h1_ok=h1_ok,
        m15_ok=m15_ok,
        heavy_m15_ok=heavy_ok,
        anti_chase_ok=anti_chase_ok,
        score_m15=m15_feats["score"],
        reasons=reasons if reasons else ["fail"]
    )
