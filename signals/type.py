from dataclasses import dataclass
from typing import List, Literal, Optional

Side = Literal["long", "short"]

@dataclass
class Candle:
    ts: int  # epoch ms
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None

@dataclass
class GateResult:
    symbol: str
    timeframe_m15_ts: int
    side: Side
    h1_ok: bool
    m15_ok: bool
    heavy_m15_ok: bool
    anti_chase_ok: bool
    score_m15: int
    reasons: List[str]
