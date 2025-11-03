# indicators.py — FINAL (safe for M5 trigger + full field set)
from __future__ import annotations
from typing import Dict, Any
import numpy as np, pandas as pd

def _safe_series(s, name: str, fill=0.0) -> pd.Series:
    if s is None:
        return pd.Series(dtype="float64", name=name)
    try:
        out = pd.Series(pd.to_numeric(s, errors="coerce").astype(float))
    except Exception:
        out = pd.Series(dtype="float64")
    out.name = name
    if out.empty:
        return out
    return out.fillna(method="ffill").fillna(fill)

def _ema(s: pd.Series, n: int) -> pd.Series:
    s = _safe_series(s, f"ema{n}")
    if s.empty: return s
    return s.ewm(span=n, adjust=False).mean()

def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    close = _safe_series(close, "close")
    if len(close) < 2: return pd.Series(index=close.index, data=np.nan, name="rsi")
    delta = close.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(n).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(n).mean()
    rs = gain / (loss.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(method="ffill").fillna(50.0)

def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    high=_safe_series(high,"high");low=_safe_series(low,"low");close=_safe_series(close,"close")
    prev_close=close.shift(1)
    tr=pd.concat([(high-low).abs(),(high-prev_close).abs(),(low-prev_close).abs()],axis=1).max(axis=1)
    return tr

def _atr(high,low,close,n=14):
    tr=_true_range(high,low,close)
    return tr.rolling(n).mean().fillna(method="ffill")

def _di_adx(high,low,close,n=14):
    high=_safe_series(high,"high");low=_safe_series(low,"low");close=_safe_series(close,"close")
    up=high.diff();down=-low.diff()
    plus_dm=up.where((up>down)&(up>0),0.0);minus_dm=down.where((down>up)&(down>0),0.0)
    tr=_true_range(high,low,close);atr=tr.rolling(n).mean()
    plus_di=100*(plus_dm.rolling(n).mean()/atr.replace(0,np.nan))
    minus_di=100*(minus_dm.rolling(n).mean()/atr.replace(0,np.nan))
    dx=(100*(plus_di-minus_di).abs()/(plus_di+minus_di).replace(0,np.nan)).fillna(0.0)
    return dx.rolling(n).mean().fillna(method="ffill")

def _bbw(close,n=20,k=2.0):
    close=_safe_series(close,"close")
    ma=close.rolling(n).mean();std=close.rolling(n).std()
    upper=ma+k*std;lower=ma-k*std
    with np.errstate(divide="ignore",invalid="ignore"):
        bbw=(upper-lower)/ma.replace(0,np.nan)
    return bbw.replace([np.inf,-np.inf],np.nan).fillna(method="ffill")

def _vwap(df: pd.DataFrame):
    if df is None or len(df)==0 or "volume" not in df: 
        return pd.Series(dtype="float64", name="vwap")
    typical=(df["high"]+df["low"]+df["close"])/3.0
    cum_vol=df["volume"].cumsum().replace(0,np.nan)
    cum_tpv=(typical*df["volume"]).cumsum()
    vwap=(cum_tpv/cum_vol).fillna(method="ffill")
    vwap.name="vwap";return vwap

def _vol_ma(s,n=20): return _safe_series(s,"volume").rolling(n).mean().fillna(method="ffill")

def _compute_one_tf(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or len(df)==0:
        return {k: pd.Series(dtype="float64") for k in
                ["df","close","volume","ema21","ema50","ema200","atr","adx","bbw","rsi","vwap","vol_ma20"]}
    df=df.copy().sort_values("timestamp").reset_index(drop=True)
    for c in ["timestamp","open","high","low","close","volume"]:
        if c not in df.columns: df[c]=np.nan
    close=_safe_series(df["close"],"close")
    high=_safe_series(df["high"],"high")
    low=_safe_series(df["low"],"low")
    vol=_safe_series(df["volume"],"volume")
    return {
        "df":df,
        "close":close,
        "volume":vol,
        "ema21":_ema(close,21),
        "ema50":_ema(close,50),
        "ema200":_ema(close,200),
        "atr":_atr(high,low,close,14),
        "adx":_di_adx(high,low,close,14),
        "bbw":_bbw(close,20,2.0),
        "rsi":_rsi(close,14),
        "vwap":_vwap(df),
        "vol_ma20":_vol_ma(vol,20)
    }

class IndicatorEngine:
    def compute_all(self, symbol:str, raw_tf:Dict[str,Any], cfg:Dict[str,Any])->Dict[str,Dict[str,Any]]:
        out={}
        for tf,wrap in (raw_tf or {}).items():
            df = wrap.get("df") if isinstance(wrap, dict) else wrap
            try: out[tf]=_compute_one_tf(df)
            except Exception: out[tf]={"df":pd.DataFrame()}
        for tf in ["M5","M15","H1","H4","D1"]:
            out.setdefault(tf, _compute_one_tf(pd.DataFrame()))
        return out
