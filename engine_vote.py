# engine_vote.py — FINAL (Adaptive Trend Mode)
from __future__ import annotations
from typing import Dict, Any, Tuple

def _resolve(cfg: dict, *keys, default=None):
    cur = cfg or {}
    for k in keys:
        cur = cur.get(k, {})
    return cur if cur else (default if default is not None else {})

def _last(series, default=0.0) -> float:
    try:
        if series is None:
            return float(default)
        if hasattr(series, "iloc"):
            return float(series.iloc[-1])
        return float(series)
    except Exception:
        return float(default)

def _ago(series, bars: int, default=0.0) -> float:
    try:
        if series is None or bars <= 0:
            return float(default)
        if hasattr(series, "iloc"):
            idx = -1 - int(bars)
            if abs(idx) <= len(series):
                return float(series.iloc[idx])
            return float(series.iloc[0])
        return float(default)
    except Exception:
        return float(default)

def _ema_slope_score(ema, lookback: int, bonus: float, penalty: float, min_bbw: float, bbw) -> float:
    try:
        if min_bbw is not None and _last(bbw, 0.0) < float(min_bbw):
            return 0.0
        cur = _last(ema, 0.0)
        prev = _ago(ema, lookback, 0.0)
        slope = cur - prev
        if slope > 0: return float(bonus)
        if slope < 0: return float(penalty)
        return 0.0
    except Exception:
        return 0.0

def _adx_slope_score(adx, lookback: int, delta_need: float, bonus: float, need_vfi_delta_pos: bool, vfi_long) -> float:
    try:
        cur = _last(adx, 0.0)
        prev = _ago(adx, lookback, 0.0)
        delta = cur - prev
        if delta >= float(delta_need):
            if need_vfi_delta_pos:
                vfi_now = _last(vfi_long, 0.0)
                vfi_prev = _ago(vfi_long, 1, 0.0)
                if vfi_now - vfi_prev <= 0:
                    return 0.0
            return float(bonus)
        return 0.0
    except Exception:
        return 0.0

def _ema_align_bias(close, ema21, ema50, ema200) -> float:
    c = _last(close); e21=_last(ema21); e50=_last(ema50); e200=_last(ema200)
    if c>e21>e50>e200:  return 0.06
    if c<e21<e50<e200:  return -0.06
    return 0.0

def _macro_adx_bias(adx: float) -> float:
    if adx >= 25: return 0.02
    if adx <= 12: return -0.01
    return 0.0

def _group_weighted(groups: Dict[str, float], weights: Dict[str, float]) -> float:
    total = 0.0
    for k, w in (weights or {}).items():
        try:
            total += float(groups.get(k, 0.0)) * float(w)
        except Exception:
            pass
    return total

def decide_side(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Input ctx:
      - indicators: {"M15": {...}, "H1": {...}, "H4": {...}, "D1": {...}}
      - config
      - group_scores: {"flow","trend","momentum","mean"}  (có thể rỗng; ta sẽ tự bổ sung)
      - vfi_scores: {"long","short"}
    Return:
      {"side": "LONG|SHORT|NEUTRAL|FLAT", "score": float, "reasons": [...], "details": {...}}
    """
    indicators: Dict[str, Dict[str, Any]] = ctx.get("indicators") or {}
    cfg = ctx.get("config") or {}
    vfi_scores = ctx.get("vfi_scores") or {"long": 0.0, "short": 0.0}
    groups = dict(ctx.get("group_scores") or {})

    # --- lấy các series cần thiết ---
    M15 = indicators.get("M15", {})
    H1  = indicators.get("H1", {})
    H4  = indicators.get("H4", {})
    D1  = indicators.get("D1", {})

    m15_close = M15.get("close"); m15_vwap = M15.get("vwap"); m15_atr = M15.get("atr"); m15_bbw = M15.get("bbw")
    h1_adx = H1.get("adx"); h1_bbw = H1.get("bbw")
    h1_close = H1.get("close"); h1_e21=H1.get("ema21"); h1_e50=H1.get("ema50"); h1_e200=H1.get("ema200")
    h4_adx = H4.get("adx"); h4_close = H4.get("close"); h4_e21=H4.get("ema21"); h4_e50=H4.get("ema50"); h4_e200=H4.get("ema200")
    d1_close = D1.get("close"); d1_e21=D1.get("ema21"); d1_e50=D1.get("ema50"); d1_e200=D1.get("ema200")

    vfi_long = indicators.get("M15", {}).get("close")  # chỉ để lấy index length an toàn
    # vfi_score đã có sẵn trong ctx['vfi_scores'], ta chỉ dùng vfi_long delta qua ctx['vfi_scores'] không đủ index
    # nên để _adx_slope_score yêu cầu need_vfi_delta_pos=False nếu thiếu series.

    # --- cấu hình chung ---
    voter = _resolve(cfg, "voter")
    long_thr  = float(voter.get("long_threshold", 0.02))
    short_thr = float(voter.get("short_threshold", -0.02))
    weights   = _resolve(cfg, "voting", "group_weights", default={"flow":0.2,"trend":0.35,"momentum":0.25,"mean":0.2})

    enhance = _resolve(cfg, "enhance", default={})
    enh_ema  = _resolve(enhance, "ema_slope", default={"enabled": False})
    enh_adx  = _resolve(enhance, "adx_slope", default={"enabled": False})
    enh_early= _resolve(enhance, "early_anticipate", default={"enabled": False})

    # --- base group scores nếu thiếu ---
    groups.setdefault("flow", float((vfi_scores.get("long",0.0) - vfi_scores.get("short",0.0)) / 100.0))
    groups.setdefault("trend", 0.0)
    groups.setdefault("momentum", 0.0)
    groups.setdefault("mean", 0.0)

    # --- macro bias H1/H4/D1 ---
    reasons = []
    trend_bias = 0.0
    # EMA alignment
    trend_bias += _ema_align_bias(h1_close, h1_e21, h1_e50, h1_e200)
    trend_bias += _ema_align_bias(h4_close, h4_e21, h4_e50, h4_e200) * 0.5  # H4 ảnh hưởng nhẹ hơn
    # ADX bias
    trend_bias += _macro_adx_bias(_last(h1_adx, 0.0))
    # D1 nghịch pha cắt bớt độ tin cậy, áp dụng ở cuối (details)
    d1_align = _ema_align_bias(d1_close, d1_e21, d1_e50, d1_e200)

    # --- EMA slope (H1/H4) ---
    slope_bonus = 0.0
    if enh_ema.get("enabled"):
        lookback = int(enh_ema.get("lookback", 3))
        bonus    = float(enh_ema.get("bonus", 0.02))
        penalty  = float(enh_ema.get("penalty", -0.02))
        min_bbw  = enh_ema.get("min_bbw", 0.10)
        slope_bonus += _ema_slope_score(h1_e21, lookback, bonus, penalty, min_bbw, h1_bbw)
        slope_bonus += 0.5 * _ema_slope_score(h4_e21, lookback, bonus, penalty, min_bbw, h1_bbw)
        if slope_bonus != 0.0:
            reasons.append(f"ema_slope:{slope_bonus:+.2f}")

    # --- ADX slope (momentum) ---
    adx_slope_bonus = 0.0
    if enh_adx.get("enabled"):
        lookback = int(enh_adx.get("lookback", 3))
        delta    = float(enh_adx.get("delta", 5))
        bonus    = float(enh_adx.get("bonus", 0.02))
        need_vfi_pos = bool(enh_adx.get("need_vfi_delta_pos", True))
        # nếu không có vfi series đầy đủ thì bỏ điều kiện vfi delta
        adx_slope_bonus += _adx_slope_score(h1_adx, lookback, delta, bonus, need_vfi_pos, vfi_long)
        if adx_slope_bonus != 0.0:
            reasons.append(f"adx_slope:{adx_slope_bonus:+.2f}")

    # --- Early anticipate (EMA21 cross EMA50 + VFI mạnh) ---
    early_bonus = 0.0
    if enh_early.get("enabled"):
        # xác định cắt 21/50 gần đây trên H1
        e21_now = _last(h1_e21, 0.0); e50_now = _last(h1_e50, 0.0)
        e21_prev = _ago(h1_e21, 1, e21_now); e50_prev = _ago(h1_e50, 1, e50_now)
        cross_up   = (e21_prev <= e50_prev) and (e21_now > e50_now)
        cross_down = (e21_prev >= e50_prev) and (e21_now < e50_now)
        min_vfi = float(enh_early.get("min_vfi", 55))
        vfi_best = max(float(vfi_scores.get("long",0.0)), float(vfi_scores.get("short",0.0)))
        if vfi_best >= min_vfi and (cross_up or cross_down):
            early_bonus = float(enh_early.get("bonus", 0.04))
            reasons.append("early_anticipate")

    # --- tổng hợp điểm gốc theo weights + bias ---
    base_score = _group_weighted(groups, weights) + trend_bias + slope_bonus + adx_slope_bonus + early_bonus

    # --- side & score ---
    side = "NEUTRAL"
    score = float(base_score)
    if score >= long_thr:   side = "LONG"
    elif score <= short_thr: side = "SHORT"
    else:
        # score nhỏ → sàn về FLAT để tránh nhiễu
        if abs(score) < 0.01:
            side = "FLAT"

    # --- D1 nghịch pha → cắt bớt confidence ---
    d1_cut = float(_resolve(cfg, "voter").get("d1_contra_conf_cut", 0.30))
    if d1_align * score < 0:  # trái pha
        score *= max(0.0, 1.0 - d1_cut)
        reasons.append("d1_contra_cut")

    # Giới hạn score bền vững
    if score > 1.0: score = 1.0
    if score < -1.0: score = -1.0

    details = {
        "trend_bias": round(trend_bias, 4),
        "slope_bonus": round(slope_bonus, 4),
        "adx_slope_bonus": round(adx_slope_bonus, 4),
        "early_bonus": round(early_bonus, 4),
        "weights": weights,
        "groups": {k: round(float(v),4) for k,v in groups.items()},
        "d1_align": round(d1_align, 4)
    }

    return {"side": side, "score": float(score), "reasons": reasons, "details": details}
