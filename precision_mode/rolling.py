from precision_mode.types import TfSnapshot, RollingH1State
from typing import Optional

def update_rolling_h1_state(
    previous_state: Optional[RollingH1State],
    h1_snapshot: TfSnapshot,
    now: int
) -> RollingH1State:
    """
    Cập nhật trạng thái rolling H1 để kiểm soát repaint.
    - Nếu điều kiện H1 thỏa mãn lần đầu: ghi nhận first_hit_at
    - Nếu vẫn thỏa mãn: cập nhật last_satisfied_at
    - Nếu không thỏa mãn: valid=False
    """
    valid = h1_snapshot.score_total >= 14  # ngưỡng có thể lấy từ config nếu cần
    first_hit_at = previous_state.first_hit_at if previous_state and previous_state.first_hit_at else None
    last_satisfied_at = previous_state.last_satisfied_at if previous_state and previous_state.last_satisfied_at else None

    if valid:
        if not first_hit_at:
            first_hit_at = now
        last_satisfied_at = now
    else:
        first_hit_at = None
        last_satisfied_at = None

    return RollingH1State(
        valid=valid,
        first_hit_at=first_hit_at,
        last_satisfied_at=last_satisfied_at
    )

def is_rolling_h1_valid(state: RollingH1State, window_seconds: int = 3600) -> bool:
    """
    Kiểm tra rolling H1 có còn hợp lệ trong cửa sổ cho phép không.
    """
    if not state.valid or not state.last_satisfied_at:
        return False
    # Cửa sổ mặc định là 1 tiếng (3600s), có thể set lại nếu cần
    from time import time
    now = int(time())
    return (now - state.last_satisfied_at) <= window_seconds
