#!/usr/bin/env bash
set -Eeuo pipefail

SVC="${1:-babysharkbot.service}"
BASE_DIR="${2:-/home/mt23veo3/BabyShark}"
VENV="$BASE_DIR/.venv"
LOG_CSV="$BASE_DIR/signals_log.csv"
LAST_JSON="$BASE_DIR/last_signal.json"

SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
fi

section() {
  echo
  echo "========== $* =========="
}

section "BASIC INFO"
echo "User: $(whoami)"
echo "Date (UTC): $(env TZ=UTC date -Is)"
echo "Host: $(hostname)"
echo "Base dir: $BASE_DIR"
echo "Service: $SVC"

section "SYSTEMD SERVICE STATUS"
if systemctl list-units --type=service | grep -q "$(basename "$SVC")"; then
  $SUDO systemctl status "$SVC" --no-pager || true
  echo
  echo "-- Service properties --"
  $SUDO systemctl show "$SVC" -p ActiveState,SubState,ExecMainPID,ExecMainStartTimestamp,Restart,RestartSec || true
else
  echo "Service $SVC not found in systemd."
fi

section "JOURNAL (LAST 300 LINES)"
$SUDO journalctl -u "$SVC" -n 300 --no-pager || true

section "RESTARTS IN LAST 24H"
$SUDO journalctl -u "$SVC" --since "24 hours ago" --no-pager | egrep -i "Starting|Started|Stopped|Failed|Restarted" | tail -n +1 | wc -l || true
$SUDO journalctl -u "$SVC" --since "24 hours ago" --no-pager | egrep -i "Starting|Started|Stopped|Failed|Restarted" | tail -n 50 || true

section "SYSTEM TIME & NTP"
timedatectl || true

section "RESOURCES SNAPSHOT"
echo "-- uptime --"; uptime || true
echo "-- memory --"; free -h || true
echo "-- disk --"; df -h / || true
echo "-- top --"; (top -b -n1 | head -n 5) || true

section "PROJECT LAYOUT"
if [ -d "$BASE_DIR" ]; then
  (cd "$BASE_DIR" && ls -la | sed -n '1,200p')
else
  echo "Base dir not found: $BASE_DIR"
fi

section "PYTHON / VENV / PACKAGES"
if [ -d "$VENV" ]; then
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  echo "Python: $(python -V 2>&1 || true)"
  echo "-- key packages --"
  pip show ccxt 2>/dev/null | egrep 'Name:|Version:' || echo "ccxt: n/a"
  pip show pandas 2>/dev/null | egrep 'Name:|Version:' || echo "pandas: n/a"
  pip show numpy 2>/dev/null | egrep 'Name:|Version:' || echo "numpy: n/a"
  pip show ta 2>/dev/null | egrep 'Name:|Version:' || echo "ta: n/a"
else
  echo "Venv not found: $VENV"
fi

section "CONFIG SUMMARY"
CFG="$BASE_DIR/config.json"
if [ -f "$CFG" ]; then
  python - <<'PY'
import json, os, sys, re
from pathlib import Path
cfg_path = Path(os.environ.get("CFG", "")) or Path(sys.argv[0]).parent.parent / "config.json"
try:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
except Exception as e:
    print(f"Failed to load config.json: {e}")
    sys.exit(0)

def get(k, default=None):
    cur = cfg
    for p in k.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

print("Top-level keys:", list(cfg.keys()))
symbols = get("symbols") or get("market.symbols")
tfs = get("timeframes") or get("market.timeframes")
print("Symbols:", (len(symbols) if isinstance(symbols, list) else symbols), symbols if isinstance(symbols, list) else "")
print("Timeframes:", tfs)

print("Voting/Weighted thresholds:")
print(" - voting:", get("voting"))
print(" - weighted:", get("weighted") or {"threshold_long": get("weighted_threshold_long"), "threshold_short": get("weighted_threshold_short")})

print("Trend filter:", get("trend_filter"))
print("Max holding:", get("max_holding"))
print("Discord config present?:", "discord" in cfg, "webhook_url" if ("discord" in cfg and isinstance(cfg["discord"], dict) and "webhook_url" in cfg["discord"]) else "token/bot?" )
PY
else
  echo "config.json not found at $CFG"
fi

section "SIGNALS LOG (LAST 50 LINES)"
if [ -f "$LOG_CSV" ]; then
  tail -n 50 "$LOG_CSV" || true
else
  echo "signals_log.csv not found."
fi

section "LAST SIGNAL JSON"
if [ -f "$LAST_JSON" ]; then
  sed -n '1,200p' "$LAST_JSON" || true
else
  echo "last_signal.json not found."
fi

section "FRESHNESS OF LAST SIGNAL"
python - <<'PY'
import os, re, csv, json, sys
from datetime import datetime, timezone
base = os.environ.get("BASE_DIR", ".")
log_csv = os.path.join(base, "signals_log.csv")
last_json = os.path.join(base, "last_signal.json")
now = datetime.now(timezone.utc)

def parse_dt(s):
    # Try common formats quickly; fallback regex
    fmts = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    s2 = s
    if s.endswith("Z"):
        s2 = s[:-1] + "+0000"
    for f in fmts:
        try:
            dt = datetime.strptime(s2, f)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except: pass
    m = re.search(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+\-]\d{2}:?\d{2})?", s)
    if m:
        ss = m.group(0)
        if ss.endswith("Z"):
            ss = ss[:-1] + "+0000"
        ss = re.sub(r"([+\-]\d{2}):(\d{2})$", r"\1\2", ss)  # +07:00 -> +0700
        for f in fmts:
            try:
                dt = datetime.strptime(ss, f)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except: pass
    return None

last_ts = None
if os.path.exists(log_csv):
    try:
        last_line = None
        with open(log_csv, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip():
                    last_line = line
        if last_line:
            dt = parse_dt(last_line)
            if not dt:
                # try CSV column
                f = open(log_csv, newline="", encoding="utf-8", errors="ignore")
                r = csv.DictReader(f)
                rows = list(r)[-1:]
                if rows:
                    for k in ("timestamp","time","ts","created_at","sent_at"):
                        if k in rows[0]:
                            dt = parse_dt(rows[0][k] or "")
                            if dt: break
            last_ts = dt
    except Exception as e:
        print("CSV parse error:", e)

if (not last_ts) and os.path.exists(last_json):
    try:
        j = json.load(open(last_json, "r", encoding="utf-8"))
        for k in ("timestamp","time","ts","created_at","sent_at"):
            if k in j:
                dt = parse_dt(str(j[k]))
                if dt:
                    last_ts = dt
                    break
    except Exception as e:
        print("JSON parse error:", e)

if last_ts:
    delta = now - last_ts
    print("Last signal (UTC):", last_ts.isoformat())
    print("Now (UTC):       ", now.isoformat())
    print("Age:", delta, f"({delta.total_seconds()/60:.1f} minutes)")
else:
    print("Unable to determine last signal timestamp.")
PY
echo
echo "Done."
