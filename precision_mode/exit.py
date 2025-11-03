from precision_mode.types import TfSnapshot
from precision_mode.config import EXIT_CONFIG

def should_exit(snapshot: TfSnapshot, entry_price: float) -> (bool, list):
    """
    Quyết định có nên thoát lệnh không dựa trên các điều kiện trailing stop, take profit, v.v.
    Trả về: (nên thoát, [lý do])
    """
    reasons = []
    if snapshot.close is None:
        return False, ["no price data"]

    # Take profit
    if snapshot.direction == "LONG":
        target = entry_price * (1 + EXIT_CONFIG["tp_pct"] / 100)
        if snapshot.close >= target:
            reasons.append(f"Take profit hit: {snapshot.close:.2f} >= {target:.2f}")
    else:  # SHORT
        target = entry_price * (1 - EXIT_CONFIG["tp_pct"] / 100)
        if snapshot.close <= target:
            reasons.append(f"Take profit hit: {snapshot.close:.2f} <= {target:.2f}")

    # Trailing stop
    if snapshot.direction == "LONG":
        stop = entry_price * (1 - EXIT_CONFIG["trailing_stop_pct"] / 100)
        if snapshot.close <= stop:
            reasons.append(f"Trailing stop hit: {snapshot.close:.2f} <= {stop:.2f}")
    else:  # SHORT
        stop = entry_price * (1 + EXIT_CONFIG["trailing_stop_pct"] / 100)
        if snapshot.close >= stop:
            reasons.append(f"Trailing stop hit: {snapshot.close:.2f} >= {stop:.2f}")

    # Custom: exit nếu score giảm mạnh
    if snapshot.score_total <= EXIT_CONFIG["min_score"]:
        reasons.append(f"Score too low: {snapshot.score_total} <= {EXIT_CONFIG['min_score']}")

    return (len(reasons) > 0, reasons)
