from typing import Dict

def _get_weights(cfg, tf):
    return cfg.get("weights_sets", {}).get(tf, {})

def _get_threshold(cfg, tf):
    return cfg.get("thresholds", {}).get(tf, 0)

def _get_neutral_bump(cfg):
    return cfg.get("thresholds", {}).get("neutral_bump", 0.3)

def _enforce_same_dir(cfg):
    return cfg.get("filter", {}).get("enforce_same_direction", True)

def score_indicators(indicators: Dict[str, str], weights: Dict[str, float]) -> Dict:
    # Dummy scoring logic, replace with your own
    score_long = 0
    score_short = 0
    side = "NEUTRAL"
    for k, v in indicators.items():
        w = weights.get(k, 1)
        if v == "LONG":
            score_long += w
        elif v == "SHORT":
            score_short += w
    if score_long > score_short and score_long > 0:
        side = "LONG"
    elif score_short > score_long and score_short > 0:
        side = "SHORT"
    return {"score_long": score_long, "score_short": score_short, "side": side}

def filter_m15_with_h1(
    indicators_m15: Dict[str, str],
    indicators_h1: Dict[str, str],
    cfg: Dict,
) -> Dict:
    """
    Filter cho M15 với H1: M15 phải đồng thuận và đủ điểm với H1
    """
    w15 = _get_weights(cfg, "M15")
    w1h = _get_weights(cfg, "H1")
    th15 = _get_threshold(cfg, "M15")
    th1h = _get_threshold(cfg, "H1")
    bump = _get_neutral_bump(cfg)
    enforce = _enforce_same_dir(cfg)

    s15 = score_indicators(indicators_m15, w15)
    s1h = score_indicators(indicators_h1, w1h)

    req_th15 = th15

    # Nếu H1 NEUTRAL -> nâng ngưỡng
    if s1h["side"] == "NEUTRAL":
        req_th15 = th15 + bump
        ok = (max(s15["score_long"], s15["score_short"]) >= req_th15)
        reason = f"H1 NEUTRAL → nâng ngưỡng M15 lên {req_th15:.2f}."
        return {
            "pass": ok,
            "m15": {**s15, "threshold": th15},
            "h1": {**s1h, "threshold": th1h},
            "required_m15_threshold": req_th15,
            "reason": reason if ok else reason + " Không đủ điểm M15.",
        }

    # Nếu enforce và chiều M15 khác H1 -> fail
    if enforce and (s15["side"] != s1h["side"]):
        return {
            "pass": False,
            "m15": {**s15, "threshold": th15},
            "h1": {**s1h, "threshold": th1h},
            "required_m15_threshold": req_th15,
            "reason": f"Chiều M15 ({s15['side']}), H1 ({s1h['side']}) không cùng hướng. Bị chặn.",
        }

    # Nếu H1 không đủ điểm
    if max(s1h["score_long"], s1h["score_short"]) < th1h:
        return {
            "pass": False,
            "m15": {**s15, "threshold": th15},
            "h1": {**s1h, "threshold": th1h},
            "required_m15_threshold": req_th15,
            "reason": f"H1 ({s1h['side']}) không đủ điểm (cần ≥ {th1h:.2f}).",
        }

    # Kiểm tra M15 đủ điểm chưa
    ok = (max(s15["score_long"], s15["score_short"]) >= th15)
    return {
        "pass": ok,
        "m15": {**s15, "threshold": th15},
        "h1": {**s1h, "threshold": th1h},
        "required_m15_threshold": req_th15,
        "reason": "M15/H1 cùng chiều và đạt ngưỡng. " + ("OK" if ok else "M15 chưa đủ điểm."),
    }

def filter_m5_with_m15_and_h1(
    indicators_m5: Dict[str, str],
    indicators_m15: Dict[str, str],
    indicators_h1: Dict[str, str],
    cfg: Dict,
) -> Dict:
    """
    Quy tắc:
      - H1 cùng chiều M15 và đều đủ điểm, M5 cùng chiều M15/H1 và đủ điểm -> pass.
      - Nếu bất kỳ khung nào NEUTRAL -> nâng ngưỡng M5.
      - Nếu bất kỳ khung nào ngược chiều -> fail.
    """
    w5 = _get_weights(cfg, "M5")
    w15 = _get_weights(cfg, "M15")
    w1h = _get_weights(cfg, "H1")
    th5 = _get_threshold(cfg, "M5")
    th15 = _get_threshold(cfg, "M15")
    th1h = _get_threshold(cfg, "H1")
    bump = _get_neutral_bump(cfg)
    enforce = _enforce_same_dir(cfg)

    s5 = score_indicators(indicators_m5, w5)
    s15 = score_indicators(indicators_m15, w15)
    s1h = score_indicators(indicators_h1, w1h)

    req_th5 = th5

    # Nếu H1 hoặc M15 NEUTRAL -> nâng ngưỡng
    if s1h["side"] == "NEUTRAL" or s15["side"] == "NEUTRAL":
        req_th5 = th5 + bump
        ok = (max(s5["score_long"], s5["score_short"]) >= req_th5)
        reason = f"H1 hoặc M15 NEUTRAL → nâng ngưỡng M5 lên {req_th5:.2f}."
        return {
            "pass": ok,
            "m5": {**s5, "threshold": th5},
            "m15": {**s15, "threshold": th15},
            "h1": {**s1h, "threshold": th1h},
            "required_m5_threshold": req_th5,
            "reason": reason if ok else reason + " Không đủ điểm M5.",
        }

    # Nếu enforce và chiều M5 khác M15 hoặc M15 khác H1 -> fail
    if enforce and (s5["side"] != s15["side"] or s15["side"] != s1h["side"]):
        return {
            "pass": False,
            "m5": {**s5, "threshold": th5},
            "m15": {**s15, "threshold": th15},
            "h1": {**s1h, "threshold": th1h},
            "required_m5_threshold": req_th5,
            "reason": f"Chiều M5 ({s5['side']}), M15 ({s15['side']}), H1 ({s1h['side']}) không cùng hướng. Bị chặn.",
        }

    # Nếu H1 hoặc M15 không đủ điểm
    if max(s1h["score_long"], s1h["score_short"]) < th1h:
        return {
            "pass": False,
            "m5": {**s5, "threshold": th5},
            "m15": {**s15, "threshold": th15},
            "h1": {**s1h, "threshold": th1h},
            "required_m5_threshold": req_th5,
            "reason": f"H1 ({s1h['side']}) không đủ điểm (cần ≥ {th1h:.2f}).",
        }
    if max(s15["score_long"], s15["score_short"]) < th15:
        return {
            "pass": False,
            "m5": {**s5, "threshold": th5},
            "m15": {**s15, "threshold": th15},
            "h1": {**s1h, "threshold": th1h},
            "required_m5_threshold": req_th5,
            "reason": f"M15 ({s15['side']}) không đủ điểm (cần ≥ {th15:.2f}).",
        }

    # Kiểm tra M5 đủ điểm chưa
    ok = (max(s5["score_long"], s5["score_short"]) >= th5)
    return {
        "pass": ok,
        "m5": {**s5, "threshold": th5},
        "m15": {**s15, "threshold": th15},
        "h1": {**s1h, "threshold": th1h},
        "required_m5_threshold": req_th5,
        "reason": "M5/M15/H1 cùng chiều và đạt ngưỡng. " + ("OK" if ok else "M5 chưa đủ điểm."),
    }
