import csv
from collections import defaultdict
from services.constants import SIGNALS_LOG

def safe_load_csv(path):
    result = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for k, v in row.items():
                    if v == "None":
                        row[k] = ""
                result.append(row)
    except Exception:
        pass
    return result

def get_all_signals():
    return safe_load_csv(SIGNALS_LOG)

def get_signal_by_id(signal_id):
    signals = safe_load_csv(SIGNALS_LOG)
    for s in signals:
        if s.get("signal_id", "") == signal_id:
            return s
    return {}

def get_signal_stats():
    signals = safe_load_csv(SIGNALS_LOG)
    count = len(signals)
    by_type = defaultdict(int)
    for s in signals:
        st = s.get("type", "unknown")
        by_type[st] += 1
    return {
        "total_signals": count,
        "by_type": dict(by_type)
    }