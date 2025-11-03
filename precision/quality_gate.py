def quality_gate(snapshot, min_score=14, min_quality=88):
    st = getattr(snapshot,"score_total",0) or 0
    qp = getattr(snapshot,"quality_pct",0) or 0
    return st >= min_score and qp >= min_quality
