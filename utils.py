import csv, os
from datetime import datetime

def ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def append_csv(path: str, fieldnames, row: dict):
    ensure_dir(path)
    exists = os.path.isfile(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        # chỉ ghi các field có trong fieldnames (tránh KeyError)
        w.writerow({k: row.get(k) for k in fieldnames})

# -------- Latency log --------
LATENCY_FIELDS = [
    "timestamp_full","symbol","side",
    "pre_time","full_time","delay_sec",
    "price_pre","price_full","delta_pct",
    "m15_score_pre","m15_score_full","h1_score_full",
    "dist_pre_atr","dist_full_atr"
]

def log_latency(row: dict):
    append_csv("latency_log.csv", LATENCY_FIELDS, row)

# -------- Scan / reason log --------
REASONS_FIELDS = [
    "timestamp","symbol","phase","side",
    "m15_score","h1_score","heavy_hits","adx_h1",
    "dist_vwap_atr","anti_chase_tier","fast_flags","decision"
]

def log_reason(row: dict):
    append_csv("entries_reasons.csv", REASONS_FIELDS, row)

# -------- Score distribution (PHẦN 1) --------
SCORES_FIELDS = [
    "timestamp","symbol","timeframe",
    "score_long","score_short","score_threshold",
    "score_total_weight","active_total_weight","status"
]

def log_score(row: dict):
    """
    status: NONE (mặc định mỗi vòng scan), LONG/SHORT (khi vào FULL).
    """
    row.setdefault("timestamp", datetime.utcnow().isoformat())
    append_csv("scores_log.csv", SCORES_FIELDS, row)

def get_now_iso():
    return datetime.utcnow().isoformat()
