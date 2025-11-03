from precision_mode.types import TfSnapshot
from precision_mode.config import ENTRY_CONFIG

def get_breakout_zone(snapshot: TfSnapshot, direction: str) -> tuple:
    """
    Trả về vùng breakout zone [min, max] dựa trên config.
    direction: "LONG" hoặc "SHORT"
    """
    offset_min, offset_max = ENTRY_CONFIG["breakout_zone_offsets"]
    if direction == "LONG":
        # breakout từ đỉnh M15
        if snapshot.prev_m15_high is not None:
            min_price = snapshot.prev_m15_high * (1 + offset_min / 100)
            max_price = snapshot.prev_m15_high * (1 + offset_max / 100)
            return (min_price, max_price)
    elif direction == "SHORT":
        # breakout từ đáy M15
        if snapshot.prev_m15_low is not None:
            min_price = snapshot.prev_m15_low * (1 - offset_max / 100)
            max_price = snapshot.prev_m15_low * (1 - offset_min / 100)
            return (min_price, max_price)
    return (None, None)

def get_pullback_zone(snapshot: TfSnapshot) -> tuple:
    """
    Trả về vùng pullback quanh EMA20/VWAP theo config.
    """
    offset = ENTRY_CONFIG["pullback_offset_pct"]
    zones = []
    if snapshot.ema20:
        zones.append((snapshot.ema20 * (1 - offset / 100), snapshot.ema20 * (1 + offset / 100)))
    if snapshot.vwap:
        zones.append((snapshot.vwap * (1 - offset / 100), snapshot.vwap * (1 + offset / 100)))
    return zones

def can_buy_through(snapshot: TfSnapshot) -> bool:
    """
    Kiểm tra điều kiện buy-through (giá gần VWAP, đủ size).
    """
    cfg = ENTRY_CONFIG["buy_through"]
    if snapshot.vwap and snapshot.close:
        dist_vwap_pct = abs(snapshot.close - snapshot.vwap) / snapshot.vwap * 100
        if dist_vwap_pct <= cfg["dist_vwap_max"] and snapshot.size >= cfg["size"]:
            return True
    return False

def is_retest_timeout(snapshot: TfSnapshot) -> bool:
    """
    Kiểm tra đã quá thời gian chờ retest entry chưa.
    """
    bars = ENTRY_CONFIG["retest_timeout_bars"]
    if snapshot.bars_since_breakout is not None and snapshot.bars_since_breakout > bars:
        return True
    return False
