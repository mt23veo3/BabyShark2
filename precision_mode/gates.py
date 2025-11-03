from precision_mode.types import TfSnapshot
from precision_mode.config import THRESHOLDS, GATES

def threshold_gate(snapshot: TfSnapshot, min_score: int, min_quality: int) -> (bool, list):
    """
    Kiểm tra điểm nền và chất lượng có đạt ngưỡng không.
    Trả về: (pass/fail, [reason])
    """
    reasons = []
    if snapshot.score_total < min_score:
        reasons.append(f"score_total {snapshot.score_total} < min {min_score}")
    if snapshot.quality_pct < min_quality:
        reasons.append(f"quality_pct {snapshot.quality_pct} < min {min_quality}")
    return (len(reasons) == 0, reasons)


def fast_slow_gate(snapshot: TfSnapshot, fast_min: int, slow_min: int) -> (bool, list):
    """
    Kiểm tra điểm nhanh/chậm có đủ không.
    Trả về: (pass/fail, [reason])
    """
    reasons = []
    if snapshot.fast_points < fast_min:
        reasons.append(f"fast_points {snapshot.fast_points} < min {fast_min}")
    if snapshot.slow_points < slow_min:
        reasons.append(f"slow_points {snapshot.slow_points} < min {slow_min}")
    return (len(reasons) == 0, reasons)


def is_adx_strong(snapshot: TfSnapshot) -> bool:
    """
    Xác định ADX M15 mạnh (có thể điều chỉnh logic nếu cần).
    """
    # Giả sử adx_rising và score_total > ngưỡng là 'mạnh'
    return bool(snapshot.adx_rising) and snapshot.score_total >= THRESHOLDS["M15"]


def range_downweight(snapshot: TfSnapshot) -> bool:
    """
    Quy tắc giảm trọng số 'Range' khi ADX mạnh. Trả về True nếu cần downweight.
    """
    if GATES.get("range_downweight_when_adx_strong", False):
        return is_adx_strong(snapshot)
    return False

def gate_summary(snapshot: TfSnapshot) -> dict:
    """
    Tổng hợp kết quả pass/fail cho từng gate, trả về dict.
    """
    res = {}
    pass_threshold, reasons_threshold = threshold_gate(
        snapshot,
        THRESHOLDS.get("M15", 14),
        THRESHOLDS.get("quality", 88)
    )
    pass_fastslow, reasons_fastslow = fast_slow_gate(
        snapshot,
        GATES.get("fast_min", 9),
        GATES.get("slow_min", 3)
    )
    res["pass_threshold"] = pass_threshold
    res["reasons_threshold"] = reasons_threshold
    res["pass_fastslow"] = pass_fastslow
    res["reasons_fastslow"] = reasons_fastslow
    res["need_range_downweight"] = range_downweight(snapshot)
    return res
