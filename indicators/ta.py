import numpy as np
import pandas as pd

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def atr(h: pd.Series, l: pd.Series, c: pd.Series, period: int = 14) -> pd.Series:
    prev_close = c.shift(1)
    tr = pd.concat([
        (h - l),
        (h - prev_close).abs(),
        (l - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(up, index=close.index).ewm(alpha=1/period, adjust=False).mean()
    roll_down = pd.Series(down, index=close.index).ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / (roll_down.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def adx(h: pd.Series, l: pd.Series, c: pd.Series, period: int = 14) -> pd.Series:
    up_move = h.diff()
    down_move = -l.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr1 = h - l
    tr2 = (h - c.shift(1)).abs()
    tr3 = (l - c.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_val = tr.rolling(window=period, min_periods=period).mean()
    plus_di = 100 * pd.Series(plus_dm, index=h.index).ewm(alpha=1/period, adjust=False).mean() / atr_val
    minus_di = 100 * pd.Series(minus_dm, index=h.index).ewm(alpha=1/period, adjust=False).mean() / atr_val
    dx = ( (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) ) * 100
    return dx.ewm(alpha=1/period, adjust=False).mean().fillna(0)

def supertrend(h: pd.Series, l: pd.Series, c: pd.Series, atr_period: int = 10, multiplier: float = 3.0) -> pd.Series:
    atr_val = atr(h, l, c, atr_period)
    basic_upperband = (h + l) / 2 + multiplier * atr_val
    basic_lowerband = (h + l) / 2 - multiplier * atr_val

    final_upperband = basic_upperband.copy()
    final_lowerband = basic_lowerband.copy()
    st = pd.Series(index=c.index, dtype=float)
    dir_long = pd.Series(index=c.index, dtype=int)  # 1 long, -1 short

    for i in range(1, len(c)):
        idx = c.index[i]
        prev_idx = c.index[i-1]

        final_upperband.iloc[i] = min(basic_upperband.iloc[i], final_upperband.iloc[i-1]) if c.iloc[i-1] > final_upperband.iloc[i-1] else basic_upperband.iloc[i]
        final_lowerband.iloc[i] = max(basic_lowerband.iloc[i], final_lowerband.iloc[i-1]) if c.iloc[i-1] < final_lowerband.iloc[i-1] else basic_lowerband.iloc[i]

        if np.isnan(st.iloc[i-1]):
            st.iloc[i-1] = basic_upperband.iloc[i-1]
            dir_long.iloc[i-1] = -1

        if c.iloc[i] > final_upperband.iloc[i-1]:
            dir_long.iloc[i] = 1
            st.iloc[i] = final_lowerband.iloc[i]
        elif c.iloc[i] < final_lowerband.iloc[i-1]:
            dir_long.iloc[i] = -1
            st.iloc[i] = final_upperband.iloc[i]
        else:
            dir_long.iloc[i] = dir_long.iloc[i-1]
            st.iloc[i] = final_lowerband.iloc[i] if dir_long.iloc[i] == 1 else final_upperband.iloc[i]

    dir_long = dir_long.fillna(method="ffill").fillna(-1)
    return dir_long  # 1 = long, -1 = short

def vwap(c: pd.Series, v: pd.Series, anchor: str = "daily_utc") -> pd.Series:
    if anchor != "daily_utc":
        raise NotImplementedError("Only daily_utc anchor is implemented")
    df = pd.DataFrame({"c": c, "v": v}).copy()
    dates = df.index.tz_convert("UTC").date if df.index.tz is not None else df.index.tz_localize("UTC").date
    df["date"] = dates
    vwap_vals = []
    cum_pv = 0.0
    cum_v = 0.0
    prev_date = None
    for i, row in df.iterrows():
        if prev_date is None or row["date"] != prev_date:
            cum_pv = 0.0
            cum_v = 0.0
            prev_date = row["date"]
        cum_pv += row["c"] * (row["v"] if not np.isnan(row["v"]) else 0.0)
        cum_v += (row["v"] if not np.isnan(row["v"]) else 0.0)
        vwap_vals.append(cum_pv / cum_v if cum_v > 0 else row["c"])
    return pd.Series(vwap_vals, index=c.index)

def range_filter_direction(c: pd.Series, h: pd.Series, l: pd.Series, length: int = 20, atr_mult: float = 1.5) -> pd.Series:
    """
    Simple ATR-banded EMA baseline. Direction flips only when price exits the band.
    Returns 1 for long, -1 for short.
    """
    base = ema(c, length)
    atr_val = atr(h, l, c, 14)
    upper = base + atr_mult * atr_val
    lower = base - atr_mult * atr_val
    direction = pd.Series(index=c.index, dtype=int)
    curr = -1
    for i in range(len(c)):
        if np.isnan(upper.iloc[i]) or np.isnan(lower.iloc[i]):
            direction.iloc[i] = curr
            continue
        if c.iloc[i] > upper.iloc[i]:
            curr = 1
        elif c.iloc[i] < lower.iloc[i]:
            curr = -1
        direction.iloc[i] = curr
    return direction.fillna(method="ffill").fillna(-1)

def slope(series: pd.Series, lookback: int = 3) -> float:
    if len(series) < lookback + 1:
        return 0.0
    return series.iloc[-1] - series.iloc[-1 - lookback]
