# tools/replay.py
# Minimal backtest/replay placeholder
import pandas as pd, json, argparse
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=False, help="OHLCV csv")
    args = p.parse_args()
    print(json.dumps({"winrate": 0.0, "pf": 0.0, "avgR": 0.0, "mdd": 0.0}))
if __name__ == "__main__":
    main()
