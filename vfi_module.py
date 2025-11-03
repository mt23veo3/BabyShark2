# vfi_module.py — BabyShark Volume Flow Intelligence
from __future__ import annotations
from typing import Dict, Optional
import pandas as pd
import numpy as np

EPS = 1e-9

def _to_num(s):
    return pd.to_numeric(s, errors="coerce")

def _safe(v):
    try:
        return float(v)
    except Exception:
        return 0.0

def _sma(s: pd.Series, n: int) -> pd.Series:
    s = _to_num(s)
    return s.rolling(n, min_periods=max(2, min(n, 5))).mean()

def _rma(s: pd.Series, n: int) -> pd.Series:
    s = _to_num(s)
    return s.ewm(alpha=1/float(n), adjust=False).mean()

def _tr(h,l,c):
    pc = _to_num(c).shift(1)
    h  = _to_num(h); l=_to_num(l)
    return pd.concat([(h-l).abs(), (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)

def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return _rma(_tr(df["high"], df["low"], df["close"]), n)

def _vwap(df: pd.DataFrame) -> pd.Series:
    tp = (_to_num(df["high"]) + _to_num(df["low"]) + _to_num(df["close"])) / 3.0
    vol = _to_num(df["volume"]).replace(0, np.nan)
    cum_pv = (tp * vol).cumsum()
    cum_v  = vol.cumsum()
    return (cum_pv / (cum_v.replace(0, np.nan))).fillna(method="ffill").fillna(method="bfill")

def calc_vfi_features(
    df_m15: pd.DataFrame,
    vwap: Optional[pd.Series] = None,
    atr:  Optional[pd.Series] = None,
    spot_df_m15: Optional[pd.DataFrame] = None
) -> Dict[str, float]:
    """
    Trích xuất features ít nhiễu, dùng cho entry/exit:
      - VSS: volume / SMA20(volume)           (0..5)
      - TBA: |body| / ATR                     (0..5)
      - WI_long/WI_short: wick/body           (0..5)
      - VP: |close - vwap| / ATR              (0..5)
      - FSD: futures/spot delta chuẩn hóa     (0.2..5, tuỳ chọn)
    """
    df = df_m15.copy()
    if df is None or len(df) < 30:
        return {"VSS":0.0,"TBA":0.0,"WI_long":0.0,"WI_short":0.0,"VP":0.0}

    c = _to_num(df["close"])
    o = _to_num(df["open"])
    h = _to_num(df["high"])
    l = _to_num(df["low"])
    v = _to_num(df["volume"]).clip(lower=0)

    if (c.iloc[-1] <= 0) or (h.iloc[-1] < l.iloc[-1]):
        return {"VSS":0.0,"TBA":0.0,"WI_long":0.0,"WI_short":0.0,"VP":0.0}

    body  = (c - o).abs()
    upper = (h - c).where(c >= o, (h - o))
    lower = (o - l).where(c >= o, (c - l))

    vol_ma20 = _sma(v, 20).replace(0, np.nan)
    VSS = (v / vol_ma20).iloc[-1] if not pd.isna(vol_ma20.iloc[-1]) else 0.0

    atr_s = atr if atr is not None else _atr(df, 14)
    ATR = _safe(atr_s.iloc[-1])
    TBA = _safe(body.iloc[-1]) / (ATR + EPS)

    body_now = _safe(body.iloc[-1])
    WI_long  = _safe(lower.iloc[-1]) / (body_now + EPS)
    WI_short = _safe(upper.iloc[-1]) / (body_now + EPS)

    vwap_s = vwap if vwap is not None else _vwap(df)
    VP = abs(_safe(c.iloc[-1]) - _safe(vwap_s.iloc[-1])) / (ATR + EPS)

    FSD = None
    if spot_df_m15 is not None and len(spot_df_m15) >= len(df) - 5:
        spot_c = _to_num(spot_df_m15["close"])
        n = min(len(spot_c), len(c))
        if n >= 20:
            diff = (c.iloc[-n:] - spot_c.iloc[-n:]).dropna()
            if len(diff) >= 20 and diff.std() > 0:
                FSD = float(np.clip(diff.iloc[-1] / (diff.std() + EPS), 0.2, 5.0))

    return {
        "VSS": float(np.clip(VSS, 0.0, 5.0)),
        "TBA": float(np.clip(TBA, 0.0, 5.0)),
        "WI_long": float(np.clip(WI_long, 0.0, 5.0)),
        "WI_short": float(np.clip(WI_short, 0.0, 5.0)),
        "VP":  float(np.clip(VP, 0.0, 5.0)),
        "FSD": None if FSD is None else float(np.clip(FSD, 0.2, 5.0)),
    }

def vfi_score(features: Dict[str, float], direction: str) -> float:
    """
    Điểm 0..100; trọng số giả định:
      VSS 40%  | TBA 30% | WI (ngược) 20% | VP 10% | *FSD là hệ số khuếch đại 0.6..2.0
    """
    VSS = _safe(features.get("VSS"))
    TBA = _safe(features.get("TBA"))
    VP  = _safe(features.get("VP"))
    WI  = _safe(features.get("WI_long" if direction == "LONG" else "WI_short"))

    base = (
        40.0 * np.clip((VSS - 1.0) / 1.5, 0.0, 1.0) +
        30.0 * np.clip((TBA - 0.7) / 0.8, 0.0, 1.0) +
        20.0 * np.clip(1.0 - np.clip(WI, 0.0, 2.0) / 1.2, 0.0, 1.0) +
        10.0 * np.clip(1.0 - np.clip(VP, 0.0, 2.0) / 1.2, 0.0, 1.0)
    )

    FSD = features.get("FSD")
    if FSD is not None:
        base *= float(np.clip(FSD, 0.6, 2.0))

    return float(np.clip(base, 0.0, 100.0))

def vfi_exit_signal(prev: Dict[str,float], now: Dict[str,float], direction: str, wick_th: float=0.8) -> str:
    """
    Tín hiệu thoát dựa trên suy yếu lực/absorption/đảo chiều footprint.
    Trả về chuỗi lý do hoặc "" nếu không có.
    """
    VSS_now = _safe(now.get("VSS"))
    TBA_now = _safe(now.get("TBA"))
    WI_now  = _safe(now.get("WI_long" if direction=="LONG" else "WI_short"))

    if VSS_now < 1.0 and TBA_now < 0.8:
        return "VFI exit: volume/body weak"
    if WI_now >= wick_th and TBA_now < 1.2:
        return "VFI exit: absorption bar"
    if prev:
        WI_prev = _safe(prev.get("WI_long" if direction=="LONG" else "WI_short"))
        if (WI_now - WI_prev) >= 0.7 and TBA_now < 1.0:
            return "VFI exit: reversal footprint"
    return ""
