# data.py — FINAL (support enhance.m5_trigger + fixed limit lookup)
from __future__ import annotations
import asyncio, time
from typing import Dict, Any, Optional, List
import ccxt

_VALID_TF = {"5m":"5m","15m":"15m","1h":"1h","4h":"4h","1d":"1d","1D":"1d"}

def _norm_tf(tf: str) -> str:
    return _VALID_TF.get(str(tf or "").strip(), str(tf or "").lower())

def build_exchange(cfg: dict) -> ccxt.binance:
    ex_cfg = cfg.get("exchange", {}) if isinstance(cfg, dict) else {}
    ex = ccxt.binance({
        "apiKey": ex_cfg.get("apiKey"),
        "secret": ex_cfg.get("secret"),
        "enableRateLimit": True,
        "options": {"defaultType": "future" if ex_cfg.get("market","FUTURES").upper()=="FUTURES" else "spot"}
    })
    ex.load_markets()
    return ex

async def fetch_ohlcv(ex: ccxt.binance, symbol: str, tf: str, *, since: Optional[int], limit: int) -> List[list]:
    tf = _norm_tf(tf)
    return await asyncio.to_thread(ex.fetch_ohlcv, symbol, timeframe=tf, since=since, limit=limit)

def to_dataframe(ohlcv: List[list]):
    import pandas as pd
    if not ohlcv:
        return pd.DataFrame(columns=["timestamp","open","high","low","close","volume"])
    df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

class DataFeed:
    def __init__(self, exchange, cfg, logger):
        self.ex = exchange
        self.cfg = cfg
        self.log = logger
        self.last_since: Dict[str,int] = {}

    async def fetch_all_timeframes(self, symbol: str) -> Dict[str, Any]:
        enh = (self.cfg.get("enhance") or {}).get("m5_trigger", {})
        need_m5 = bool(enh.get("enabled", False))
        tfs = ["M15","H1","H4","D1"]
        if need_m5: tfs.insert(0, "M5")

        map_tf = {"M5":"5m","M15":"15m","H1":"1h","H4":"4h","D1":"1d"}
        tasks = [self._fetch_tf(symbol, map_tf[tf]) for tf in tfs]
        res = await asyncio.gather(*tasks, return_exceptions=True)

        out: Dict[str,Any] = {}
        for tf, r in zip(tfs, res):
            if isinstance(r, Exception):
                self.log.error(f"[DATA][{symbol}][{tf}] fetch error: {r}")
                continue
            out[tf] = r
        return out

    async def _fetch_tf(self, symbol: str, ccxt_tf: str) -> Dict[str, Any]:
        tf_key = {"5m":"M5","15m":"M15","1h":"H1","4h":"H4","1d":"D1"}[ccxt_tf]
        lim = int(self.cfg.get("data",{}).get("limit",{}).get(tf_key, 200))
        use_inc = bool(self.cfg.get("data",{}).get("incremental", True))
        ms_now = int(time.time()*1000)
        key = f"{symbol}:{ccxt_tf}"
        since = self.last_since.get(key) if use_inc else None
        ohlcv = await fetch_ohlcv(self.ex, symbol, ccxt_tf, since=since, limit=lim)
        if ohlcv:
            self.last_since[key] = max(ohlcv[-1][0] - 1, ms_now - 3600*1000)
        df = to_dataframe(ohlcv)
        if len(df):
            sanity = self.cfg.get("data",{}).get("sanity",{})
            if sanity.get("reject_zero_close", True):
                df = df[df["close"] > 0]
            if sanity.get("reject_high_lt_low", True):
                df = df[df["high"] >= df["low"]]
        return {"df": df}
