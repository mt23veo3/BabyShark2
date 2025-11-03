def in_early_trigger_window(snapshot, bars=3):
    return (getattr(snapshot,"bars_since_breakout",None) or 0) <= bars
def early_trigger_score(snapshot, quality_thr=85, bonus=3, quality_bonus=2):
    score=0
    if in_early_trigger_window(snapshot): score+=bonus
    if (getattr(snapshot,"quality_pct",0) or 0) >= quality_thr: score+=quality_bonus
    return score
