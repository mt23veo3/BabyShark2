from precision_mode.types import TfSnapshot
from precision_mode.late_filter import check_late_filters
from precision_mode.entry import get_breakout_zone, get_pullback_zone, can_buy_through, is_retest_timeout
from precision_mode.early_trigger import in_early_trigger_window, early_trigger_score
from precision_mode.exit import should_exit

def suggest_signal(snapshot: TfSnapshot, entry_price: float = None) -> dict:
    """
    Đề xuất tín hiệu giao dịch dựa trên các module đã cài.
    Trả về dict: {"action": ..., "reason": [...], ...}
    """
    # 1. Nếu đang có tín hiệu thoát lệnh
    if entry_price is not None:
        exit_flag, reasons = should_exit(snapshot, entry_price)
        if exit_flag:
            return {"action": "EXIT", "reason": reasons}

    # 2. Kiểm tra filter muộn
    passed, reasons = check_late_filters(snapshot)
    if not passed:
        return {"action": "FILTERED_OUT", "reason": reasons}

    # 3. Kiểm tra cửa sổ entry
    if in_early_trigger_window(snapshot):
        score = early_trigger_score(snapshot)
        if score > 0:
            return {"action": "ENTRY_EARLY", "reason": [f"Early trigger score {score}"]}
    else:
        # Kiểm tra vùng breakout / pullback
        breakout_zone = get_breakout_zone(snapshot, snapshot.direction)
        pullback_zones = get_pullback_zone(snapshot)
        # ...tùy logic: kiểm tra giá hiện tại có nằm trong vùng nào không
        if breakout_zone[0] and breakout_zone[1]:
            if breakout_zone[0] <= snapshot.close <= breakout_zone[1]:
                return {"action": "ENTRY_BREAKOUT", "reason": ["In breakout zone"]}
        for zone in pullback_zones:
            if zone[0] <= snapshot.close <= zone[1]:
                return {"action": "ENTRY_PULLBACK", "reason": ["In pullback zone"]}

    # 4. Nếu không có tín hiệu đặc biệt
    return {"action": "NO_SIGNAL", "reason": []}
