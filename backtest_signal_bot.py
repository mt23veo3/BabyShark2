import csv
from precision_mode.types import TfSnapshot
from precision_mode.signal_bot import suggest_signal

def load_snapshots_from_csv(filepath):
    snapshots = []
    with open(filepath, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            snap = TfSnapshot(
                close=float(row["close"]),
                direction=row["direction"],
                score_total=int(row["score_total"]),
                quality_pct=int(row["quality_pct"]),
                fast_points=int(row["fast_points"]),
                slow_points=int(row["slow_points"]),
                bars_since_breakout=int(row["bars_since_breakout"]),
                prev_m15_high=float(row["prev_m15_high"]) if row.get("prev_m15_high") else None,
                # ... bổ sung các trường khác nếu có
            )
            snapshots.append(snap)
    return snapshots

def main():
    snapshots = load_snapshots_from_csv("data/snapshots.csv")
    entry_price = 100  # hoặc đọc từ dữ liệu nếu cần
    stats = {"ENTRY": 0, "EXIT": 0, "NO_SIGNAL": 0, "FILTERED_OUT": 0}
    with open("backtest_results.log", "w") as logfile:
        for i, snap in enumerate(snapshots):
            result = suggest_signal(snap, entry_price=entry_price)
            logfile.write(f"{i+1},{result['action']},{snap.close},{result['reason']}\n")
            # Thống kê
            key = result["action"]
            if key in stats:
                stats[key] += 1
            else:
                stats[key] = 1
    print("Backtest stats:", stats)

if __name__ == "__main__":
    main()
