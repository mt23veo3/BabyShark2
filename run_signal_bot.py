import logging
from precision_mode.types import TfSnapshot
from precision_mode.signal_bot import suggest_signal

# Cấu hình logging
logging.basicConfig(
    filename="signal_bot.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

def get_sample_snapshots():
    return [
        TfSnapshot(close=100, direction="LONG", score_total=20, quality_pct=95, fast_points=10, slow_points=5, bars_since_breakout=1),
        TfSnapshot(close=101, direction="LONG", score_total=20, quality_pct=95, fast_points=10, slow_points=5, prev_m15_high=100),
        TfSnapshot(close=99, direction="LONG", score_total=8, quality_pct=90, fast_points=10, slow_points=5),
        TfSnapshot(close=120, direction="LONG", score_total=20, quality_pct=95, fast_points=10, slow_points=5),
    ]

def log_signal(snapshot, result):
    msg = (
        f"Action: {result['action']} | "
        f"Close: {snapshot.close} | "
        f"Direction: {snapshot.direction} | "
        f"Reason: {result['reason']}"
    )
    logging.info(msg)

def main():
    snapshots = get_sample_snapshots()
    entry_price = 100
    for i, snap in enumerate(snapshots):
        result = suggest_signal(snap, entry_price=entry_price)
        print(f"Snapshot {i+1}:")
        print(f"  Action: {result['action']}")
        print(f"  Reason: {result['reason']}")
        print(f"  Close: {snap.close}")
        print()
        log_signal(snap, result)

if __name__ == "__main__":
    main()
