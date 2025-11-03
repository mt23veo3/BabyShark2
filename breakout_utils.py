# breakout_utils.py
from __future__ import annotations

from typing import Optional
import math

import pandas as pd


def candle_body(o: float, c: float) -> float:
    return abs(float(c) - float(o))


def upper_wick(h: float, o: float, c: float) -> float:
    return max(0.0, float(h) - max(float(o), float(c)))


def lower_wick(l: float, o: float, c: float) -> float:
    return max(0.0, min(float(o), float(c)) - float(l))


def rolling_mean_safe(series: pd.Series, window: int) -> float:
    if series is None or len(series) < window:
        return float("nan")
    val = series.rolling(window).mean().iloc[-1]
    return float(val) if pd.notna(val) else float("nan")


def is_breakout_ok(
    m15_df: pd.DataFrame,
    ema_series: Optional[pd.Series] = None,
    *,
    body_mult: float = 1.0,
    vol_mult: float = 1.2,
    lookback: int = 20,
) -> bool:
    """
    Xác nhận breakout nến hiện tại dựa trên:
      - Thân nến >= body_mult * SMA(body, lookback)
      - Volume   >= vol_mult  * SMA(volume, lookback)
      - (tùy chọn) Close ở phía thuận so với EMA (nếu có)
    Dùng cực kỳ an toàn: nếu thiếu dữ liệu => trả về False.
    """
    try:
        if m15_df is None or len(m15_df) < (lookback + 2):
            return False

        c_row = m15_df.iloc[-1]
        p_row = m15_df.iloc[-2]

        body_now = candle_body(c_row["open"], c_row["close"])
        body_mean = (m15_df["close"] - m15_df["open"]).abs().rolling(lookback).mean().iloc[-2]
        vol_now = float(c_row["volume"])
        vol_mean = m15_df["volume"].rolling(lookback).mean().iloc[-2]

        if any(pd.isna(x) for x in (body_now, body_mean, vol_now, vol_mean)):
            return False

        body_ok = body_now >= body_mult * float(body_mean)
        vol_ok = vol_now >= vol_mult * float(vol_mean)

        ema_ok = True
        if ema_series is not None and len(ema_series) >= 1:
            ema_ok = float(c_row["close"]) > float(ema_series.iloc[-1])

        return bool(body_ok and vol_ok and ema_ok)
    except Exception:
        # an toàn mặc định
        return False


def is_wick_trap(
    vfi_features: dict,
    direction: str,
    *,
    tba_weak: float = 1.0,
    wick_absorb_thresh: float = 1.2,
) -> bool:
    """
    Phát hiện “wick trap” theo chiều giao dịch:
      - TBA (|body|/ATR) nhỏ => lực thân yếu
      - Wick theo chiều giao dịch lớn => dễ bị hút thanh khoản
    """
    if not vfi_features:
        return False

    wick_dir = vfi_features.get("WI_long") if direction == "LONG" else vfi_features.get("WI_short")
    tba = vfi_features.get("TBA")

    if wick_dir is None or tba is None:
        return False

    try:
        wick_dir = float(wick_dir)
        tba = float(tba)
    except Exception:
        return False

    return (tba < float(tba_weak)) and (wick_dir >= float(wick_absorb_thresh))
