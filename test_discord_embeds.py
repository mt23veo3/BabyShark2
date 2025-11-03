from __future__ import annotations
import os
from BabyShark.discord_bot import send_action, send_signal

WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL") or "https://discordapp.com/api/webhooks/1417032780256120903/crK7-rRiqB_FmYwhBaM0pNYq-NCfscUSadM8P7AYRvY303QDR_tmhojNWXQU9YuAdhGm"

# Test action embed
send_action(WEBHOOK, {
    "symbol": "ADA/USDT",
    "timeframe": "15m",
    "side": "LONG",
    "action": "FILL_PROBE",
    "price": 0.9013,
    "size": 14763.19885,
    "note": "Test action"
})

# Test signal embed
send_signal(WEBHOOK, {
    "symbol": "LINKUSDT",
    "timeframe": "15m",
    "signal": "LONG",
    "entry": 24.8300,
    "sl": 24.3300,
    "tp": 25.5700,
    "votes_long": 9,
    "votes_short": 1,
    "indicators": {"ADX":"-","BollingerBands":"LONG","Chaikin_MF":"LONG","EMA200":"LONG","MA50":"LONG","MACD":"LONG",
                   "Range":"SHORT","RSI":"LONG","StochRSI":"LONG","Supertrend":"LONG","Volume_Spike":"-","VWAP":"LONG"},
    "score_long": 15.4, "score_short": 1.5
})
print("Done.")
