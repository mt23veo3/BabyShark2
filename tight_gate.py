import json, os, time
from typing import Dict, Tuple

def _normalize_key(name: str) -> str:
    return name.strip().replace(" ", "").replace("-", "").replace("_", "").upper()

def build_indicator_results(ohlcv, indicators):
    return {
        'EMA200': "LONG" if ohlcv['close'].iloc[-1] > indicators['ema200'].iloc[-1] else "SHORT",
        'MA50': "LONG" if ohlcv['close'].iloc[-1] > indicators['ma50'].iloc[-1] else "SHORT",
        'MACD': "LONG" if indicators['macd'].iloc[-1] > indicators['macd_signal'].iloc[-1] else "SHORT",
        'RSI': "LONG" if indicators['rsi'].iloc[-1] > 55 else ("SHORT" if indicators['rsi'].iloc[-1] < 45 else "-"),
        'ADX': "-",
        'VWAP': "LONG" if ohlcv['close'].iloc[-1] > indicators['vwap'].iloc[-1] else "SHORT",
        'Supertrend': "LONG" if indicators['supertrend'].iloc[-1] == 1 else "SHORT",
        'Range': "LONG" if indicators['range_filter'].iloc[-1] == 1 else "SHORT",
        'Chaikin_MF': "LONG" if indicators['chaikin_mf'].iloc[-1] > 0 else "SHORT",
        'Volume_Spike': "LONG" if indicators['volume_spike'].iloc[-1] == 1 else "-",
        'StochRSI': "LONG" if indicators['stoch_rsi'].iloc[-1] > 0.8 else ("SHORT" if indicators['stoch_rsi'].iloc[-1] < 0.2 else "-"),
        'BollingerBands': (
            "LONG" if ohlcv['close'].iloc[-1] > indicators['bollinger_bands_upper'].iloc[-1]
            else ("SHORT" if ohlcv['close'].iloc[-1] < indicators['bollinger_bands_lower'].iloc[-1] else "-")
        )
    }

def _heavy_hits(h1_map: Dict[str,str], ema200_series, side: str) -> int:
    """
    Đếm số lượng các chỉ báo EMA200, Supertrend, Range trên H1 đồng pha với side,
    so sánh key đã được normalize để tránh lỗi không khớp tên.
    """
    if side == "NEUTRAL": return 0
    want = "LONG" if side == "LONG" else "SHORT"
    keys = [_normalize_key(k) for k in ("EMA200", "Supertrend", "Range")]
    hits = 0
    # Normalize key khi so sánh
    for want_key in keys:
        for k, v in h1_map.items():
            if _normalize_key(k) == want_key and v == want:
                hits += 1
                break  # Một key chỉ tính một lần
    return hits

def anti_chase_ok(m15, ind_m15, mult: float=0.5) -> Tuple[bool,float,float,float]:
    price = float(m15["close"].iloc[-1])
    vwap = float(ind_m15["vwap"].iloc[-1])
    atr = float(ind_m15["atr"].iloc[-1]) if ind_m15.get("atr") is not None else 0.0
    dist = abs(price - vwap)
    return (dist <= mult * atr), price, vwap, atr

class StablePassTracker:
    def __init__(self, path="tight_state.json", min_gap_sec=300, required_passes=2):
        self.path = path
        self.min_gap = int(min_gap_sec)
        self.req = int(required_passes)
        self.state = self._load()
    def _load(self):
        if os.path.exists(self.path):
            try:
                return json.load(open(self.path, "r", encoding="utf-8"))
            except Exception: pass
        return {}
    def _save(self):
        try:
            json.dump(self.state, open(self.path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        except Exception: pass
    def update(self, symbol, timeframe, side, gates_ok, now_ts=None):
        if now_ts is None: now_ts = time.time()
        key = f"{symbol}|{timeframe}"
        st = self.state.get(key) or {"last_side": None, "count": 0, "last_ts": 0.0}
        if not gates_ok or side == "NEUTRAL":
            st.update({"last_side": None, "count": 0, "last_ts": now_ts})
            self.state[key] = st; self._save(); return False
        if st["last_side"] != side:
            st.update({"last_side": side, "count": 1, "last_ts": now_ts})
        else:
            if now_ts - float(st["last_ts"]) >= self.min_gap:
                st["count"] = int(st.get("count",0)) + 1
                st["last_ts"] = now_ts
        self.state[key] = st; self._save()
        return int(st["count"]) >= self.req
# =======================================
# VFI (Volume Footprint Intelligence) helpers
# =======================================

import numpy as np

def _clamp(x, lo, hi):
    try:
        return max(lo, min(hi, float(x)))
    except Exception:
        return lo

def whale_pressure_index(features: dict, direction: str) -> float:
    """
    Tính Whale Pressure Index (WPI) 0–100.
    direction: "LONG" hoặc "SHORT" => chọn wick theo hướng.
    """
    VSS = float(features.get("VSS") or 0.0)
    TBA = float(features.get("TBA") or 0.0)
    VP  = float(features.get("VP")  or 0.0)
    WI  = float(features.get("WI_long") if direction == "LONG" else features.get("WI_short") or 0.0)
    FSD = features.get("FSD")

    base = (
        40.0 * _clamp((VSS - 1.0) / 1.5, 0.0, 1.0)
        + 30.0 * _clamp((TBA - 0.7) / 0.8, 0.0, 1.0)
        + 20.0 * max(0.0, 1.0 - _clamp(WI, 0.0, 2.0) / 1.2)
        + 10.0 * max(0.0, 1.0 - _clamp(VP, 0.0, 2.0) / 1.2)
    )

    if FSD is not None:
        base *= _clamp(float(FSD), 0.6, 2.0)

    return float(round(_clamp(base, 0.0, 100.0), 2))


def vfi_detects_weak_retrace(features: dict, direction: str, cfg: dict) -> bool:
    """
    Phát hiện 'hồi trap' (pullback yếu / test thanh khoản).
    Đọc ngưỡng từ cfg['vfi'].
    """
    vfi_cfg = (cfg or {}).get("vfi", {}) or {}
    vol_th  = float(vfi_cfg.get("weak_vol_ratio", 1.2))
    body_th = float(vfi_cfg.get("weak_body_ratio", 0.8))
    wick_th = float(vfi_cfg.get("wick_absorb_thresh", 1.2))
    vp_max  = float(vfi_cfg.get("vp_max_for_weak", 1.2))

    VSS = float(features.get("VSS") or 0.0)
    TBA = float(features.get("TBA") or 0.0)
    VP  = float(features.get("VP")  or 0.0)
    WI  = float(features.get("WI_long") if direction == "LONG" else features.get("WI_short") or 0.0)

    weak_vol  = VSS < vol_th
    weak_body = TBA < body_th
    absorb    = WI > wick_th
    vwap_ok   = VP <= vp_max

    return bool(weak_vol and weak_body and absorb and vwap_ok)


def vfi_exit_signal(vfi_now: dict, vfi_prev: dict, direction: str, cfg: dict) -> str:
    """
    Kiểm tra tín hiệu thoát lệnh (exit guard):
      - whales ngược hướng mạnh
      - volume cạn / exhaustion bar
    Trả về string lý do hoặc "" nếu không có.
    """
    if vfi_now is None:
        return ""
    vfi_cfg = (cfg or {}).get("vfi", {}) or {}
    wick_th = float(vfi_cfg.get("wick_absorb_thresh", 1.2))

    # Các chỉ số hiện tại
    VSS = float(vfi_now.get("VSS") or 0.0)
    TBA = float(vfi_now.get("TBA") or 0.0)
    WI  = float(vfi_now.get("WI_long") if direction == "LONG" else vfi_now.get("WI_short") or 0.0)

    prev_WPI = float(vfi_prev.get("WPI_dir") or 0.0)
    now_WPI  = float(vfi_now.get("WPI_dir") or 0.0)

    # Điều kiện thoát
    if VSS < 1.0 and TBA < 0.8:
        return "Volume cạn – trend yếu"
    if (prev_WPI - now_WPI) >= 30.0 and WI >= wick_th:
        return "Absorption bar – exhaustion"
    if now_WPI >= 70.0:
        return "Whale reversal footprint"
    return ""
