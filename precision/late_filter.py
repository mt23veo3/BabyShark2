def late_filter(snapshot, max_wick_ratio=0.35, **kwargs):
    return (getattr(snapshot,"wick_ratio",0) or 0) <= max_wick_ratio
