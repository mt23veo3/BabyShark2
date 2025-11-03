from dataclasses import dataclass
from typing import Optional

@dataclass
class TfSnapshot:
    close: float
    direction: str
    score_total: int
    quality_pct: int
    fast_points: int
    slow_points: int
    prev_m15_high: Optional[float] = None
    prev_m15_low: Optional[float] = None
    ema20: Optional[float] = None
    vwap: Optional[float] = None
    atr: Optional[float] = None
    bars_since_breakout: Optional[int] = None
    adx_rising: Optional[bool] = None
    volume_spike: Optional[bool] = None
    zscore_bandwidth: Optional[float] = None
    size: Optional[float] = None  
