from precision_mode.types import TfSnapshot
from precision_mode.config import LATE_FILTER

def check_late_filters(snapshot: TfSnapshot) -> (bool, list):
    """
    Kiểm tra các bộ lọc muộn sau khi điều kiện nền đã pass.
    Trả về: (pass/fail, [reason])
    """
    reasons = []
    if snapshot.bars_since_breakout is not None:
        if snapshot.bars_since_breakout > LATE_FILTER["max_bars_since_breakout"]:
            reasons.append(f"bars_since_breakout {snapshot.bars_since_breakout} > max {LATE_FILTER['max_bars_since_breakout']}")
    if snapshot.vwap and snapshot.close:
        dist_vwap_pct = abs(snapshot.close - snapshot.vwap) / snapshot.vwap * 100
        if dist_vwap_pct > LATE_FILTER["max_dist_vwap_pct"]:
            reasons.append(f"dist_vwap_pct {dist_vwap_pct:.2f} > max {LATE_FILTER['max_dist_vwap_pct']}")
    if snapshot.ema20 and snapshot.close:
        dist_ema20_pct = abs(snapshot.close - snapshot.ema20) / snapshot.ema20 * 100
        if dist_ema20_pct > LATE_FILTER["max_dist_ema20_pct"]:
            reasons.append(f"dist_ema20_pct {dist_ema20_pct:.2f} > max {LATE_FILTER['max_dist_ema20_pct']}")
    if LATE_FILTER["block_volume_climax"] and snapshot.volume_spike:
        reasons.append(f"volume_spike detected, block")
    if snapshot.zscore_bandwidth is not None:
        if snapshot.zscore_bandwidth > LATE_FILTER["max_zscore_bandwidth"]:
            reasons.append(f"zscore_bandwidth {snapshot.zscore_bandwidth:.2f} > max {LATE_FILTER['max_zscore_bandwidth']}")
    return (len(reasons) == 0, reasons)
