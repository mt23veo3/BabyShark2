from typing import Any, Dict

try:
    from utils import log_score
except Exception:
    log_score = None  # fallback nếu chưa import được

def generate_signal(
    indicators, ohlcv_df, config,
    symbol=None, timeframe=None,
    trend_h4=None, trend_d1=None,
    filter_note=None, indicator_results=None,
    votes_long=0, votes_short=0, debug=None
):
    """
    Bước 1 bổ sung:
      - Luôn log score_long/score_short + threshold vào scores_log.csv
      - In debug khi không đạt ngưỡng
    """
    last = -1
    score_threshold = float(config.get('score_threshold', 13.0))

    common = {
        'symbol': symbol,
        'timeframe': timeframe,
        'trend_h4': trend_h4,
        'trend_d1': trend_d1,
        'note': filter_note,
        'indicators': indicator_results
    }

    # Lấy weights theo timeframe hiện tại
    tf_raw = config.get('timeframe') or 'M15'
    tf_key = 'M15' if str(tf_raw).lower() in ['15m', 'm15', '15', 'm15'] else 'H1'
    weights_sets = config.get('weights_sets', {}) or {}
    weights = weights_sets.get(tf_key, {})

    from votes import tally_votes
    vote_result = tally_votes(indicator_results or {}, weights)

    score_long = float(vote_result.get("score_long", 0.0))
    score_short = float(vote_result.get("score_short", 0.0))
    total_weight = vote_result.get("total_weight")
    active_total = vote_result.get("active_total_weight")

    # Quyết định trạng thái
    best = max(score_long, score_short)
    status = "NONE"
    direction = None

    # Debug & logging trước khi return
    if best < score_threshold:
        print(f"[DBG][{symbol} {timeframe}] L:{score_long:.2f} S:{score_short:.2f} < th:{score_threshold:.2f} → NONE")
        if log_score:
            log_score({
                "symbol": symbol,
                "timeframe": timeframe,
                "score_long": score_long,
                "score_short": score_short,
                "score_threshold": score_threshold,
                "score_total_weight": total_weight,
                "active_total_weight": active_total,
                "status": status
            })
        return None

    # Xác định LONG / SHORT
    if score_long >= score_threshold and score_long >= score_short:
        direction = "LONG"
        status = "LONG"
    elif score_short >= score_threshold:
        direction = "SHORT"
        status = "SHORT"
    else:
        # Trường hợp lý thuyết không tới vì best >= threshold đã lọc ở trên
        status = "NONE"
        if log_score:
            log_score({
                "symbol": symbol,
                "timeframe": timeframe,
                "score_long": score_long,
                "score_short": score_short,
                "score_threshold": score_threshold,
                "score_total_weight": total_weight,
                "active_total_weight": active_total,
                "status": status
            })
        return None

    # Giá & SL/TP (giữ nguyên logic cũ)
    entry = float(ohlcv_df['close'].iloc[last])
    if direction == "LONG":
        sl = entry * 0.98
        tp = entry * 1.03
    else:
        sl = entry * 1.02
        tp = entry * 0.97

    atr = indicators.get('atr') if indicators else None
    if atr is not None:
        try:
            atr_val = atr.iloc[last] if hasattr(atr, 'iloc') else float(atr)
        except Exception:
            atr_val = None
    else:
        atr_val = None

    if atr_val:
        stop_distance = abs(entry - sl)
        alpha = config.get("max_holding_alpha", 2.0)
        max_limit = config.get("max_holding_max", 8)
        min_limit = config.get("max_holding_min", 2)
        est_holding = int(alpha * stop_distance / atr_val) if atr_val != 0 else min_limit
        max_holding = min(max_limit, max(min_limit, est_holding))
    else:
        max_holding = config.get("max_holding_default", 3)

    max_holding_text = f"{max_holding} nến {config.get('timeframe','')}"

    signal_obj: Dict[str, Any] = {
        **common,
        'signal': direction,
        'entry': round(entry, 2),
        'sl': round(sl, 2),
        'tp': round(tp, 2),
        'votes_long': votes_long,
        'votes_short': votes_short,
        'score_long': score_long,
        'score_short': score_short,
        'score_total': total_weight,          # giúp embed/quality
        'debug': debug,
        'max_holding_candles': max_holding,
        'max_holding_text': max_holding_text,
    }

    print(f"[SIG][{symbol} {timeframe}] {direction} L:{score_long:.2f} S:{score_short:.2f} th:{score_threshold:.2f}")

    if log_score:
        log_score({
            "symbol": symbol,
            "timeframe": timeframe,
            "score_long": score_long,
            "score_short": score_short,
            "score_threshold": score_threshold,
            "score_total_weight": total_weight,
            "active_total_weight": active_total,
            "status": status
        })

    return signal_obj
