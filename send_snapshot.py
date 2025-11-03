import requests
import time
import csv

api_url = "http://127.0.0.1:5000/suggest_signal"
binance_url = "https://api.binance.com/api/v3/klines"
params = {
    "symbol": "BTCUSDT",
    "interval": "1m",
    "limit": 1
}

with open('signal_log.csv', 'a', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['timestamp', 'action', 'reason', 'close'])

    while True:
        candle = requests.get(binance_url, params=params).json()[0]
        snapshot = {
            "close": float(candle[4]),
            "direction": "LONG",
            "score_total": 20,
            "quality_pct": 95,
            "fast_points": 10,
            "slow_points": 5,
            "bars_since_breakout": 1,
            "prev_m15_high": float(candle[2]),
            "entry_price": float(candle[4])
        }
        response = requests.post(api_url, json=snapshot)
        result = response.json()
        print(result)
        writer.writerow([candle[0], result.get('action'), result.get('reason'), candle[4]])
        time.sleep(60)
