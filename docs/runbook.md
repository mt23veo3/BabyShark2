# BabyShark Runbook
- Start: `python main.py --symbols BTC/USDT --timeframes m5,m15,h1`
- Stop: `Ctrl+C` (graceful), or `systemctl restart babysharkbot`
- Logs: `votes.csv`, `entries_reasons.csv`, `orders.csv`, `telemetry_gates.csv`
- Health: script `babyshark_healthcheck.sh`
