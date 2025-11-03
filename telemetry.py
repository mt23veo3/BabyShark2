# telemetry.py
import csv, json, time
from pathlib import Path

class Telemetry:
    def __init__(self, path="telemetry_gates.csv"):
        self.path = Path(path)
        if not self.path.exists():
            with self.path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["ts","gate","ok","reason","metrics_json"])
    def log_gate(self, gate, ok, reason="", metrics=None):
        with self.path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([int(time.time()), gate, int(bool(ok)), reason, json.dumps(metrics or {})])
