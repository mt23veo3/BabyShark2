from flask import Flask, request, jsonify
from precision_mode.types import TfSnapshot
from precision_mode.signal_bot import suggest_signal

app = Flask(__name__)

@app.route("/suggest_signal", methods=["POST"])
def suggest_signal_api():
    data = request.json
    # Chuyển dữ liệu JSON đầu vào thành snapshot
    snap = TfSnapshot(
        close=float(data["close"]),
        direction=data["direction"],
        score_total=int(data["score_total"]),
        quality_pct=int(data["quality_pct"]),
        fast_points=int(data["fast_points"]),
        slow_points=int(data["slow_points"]),
        bars_since_breakout=int(data["bars_since_breakout"]),
        prev_m15_high=float(data.get("prev_m15_high", 0)),
        # ... có thể bổ sung các trường khác nếu cần
    )
    entry_price = float(data.get("entry_price", snap.close))
    result = suggest_signal(snap, entry_price=entry_price)
    return jsonify(result)

if __name__ == "__main__":
    app.run(port=5000)
