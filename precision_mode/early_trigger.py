from precision_mode.types import TfSnapshot
from precision_mode.config import EARLY_TRIGGER

def in_early_trigger_window(snapshot: TfSnapshot) -> bool:
    """
    Kiểm tra xem snapshot có nằm trong cửa sổ kích hoạt sớm không.
    Ví dụ: breakout vừa xảy ra, số bar kể từ breakout <= ngưỡng.
    """
    bars = EARLY_TRIGGER["early_trigger_max_bars"]
    if snapshot.bars_since_breakout is not None:
        return snapshot.bars_since_breakout <= bars
    return False

def early_trigger_score(snapshot: TfSnapshot) -> int:
    """
    Tính điểm ưu tiên cho entry sớm, ví dụ dựa trên score hoặc chất lượng.
    """
    score = 0
    if in_early_trigger_window(snapshot):
        score += EARLY_TRIGGER["bonus_score"]
    if snapshot.quality_pct >= EARLY_TRIGGER["quality_threshold"]:
        score += EARLY_TRIGGER["quality_bonus"]
    return score
