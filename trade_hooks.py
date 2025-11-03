# trade_hooks.py
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
import time
import math

# =========================
# 1) OPEN HOOK (Discord)
# =========================
def install_trade_open_hook(simulator, notifier):
    """
    Móc điểm mở lệnh để gửi thông báo lên Discord (nếu simulator hỗ trợ callback).
    Nếu strategy đã tự gọi notifier.signal_open(...) thì hook này coi như no-op.
    """
    if simulator is None or notifier is None:
        return

    # Simulator có danh sách callback?
    if hasattr(simulator, "on_open_callbacks"):
        cbs = getattr(simulator, "on_open_callbacks", None)
        if isinstance(cbs, list):
            cbs.append(lambda trade: _notify_open_trade(trade, notifier))
        return
    # Nếu simulator không có callback, strategy nên tự gọi _notify_open_trade sau open_trade().


def _notify_open_trade(trade: Dict[str, Any], notifier):
    """
    Chuẩn hoá dữ liệu và gửi notifier.signal_open(...).
    Bỏ qua yên lặng nếu thiếu field.
    """
    try:
        symbol = trade.get("symbol")
        direction = trade.get("direction")
        entry = float(trade.get("entry"))
        sl = float(trade.get("sl"))
        tp = float(trade.get("tp"))
        setup = trade.get("setup") or ("SIDEWAY" if trade.get("sideway") else "TREND")
        extra = trade.get("reason") or ""
        notifier.signal_open(setup, symbol, direction, entry, sl, tp, extra)
    except Exception:
        pass


# =========================
# 2) EARLY PROBE / PROMOTE
# =========================
def should_open_early_probe(*, side_m15: str, anti_chase_ok: bool, snapshot_ok: bool) -> bool:
    """
    Cho phép mở probe sớm khi:
      - đã có hướng M15 rõ ràng (LONG/SHORT)
      - qua anti-chase VWAP
      - snapshot M5 xác nhận (require_bars=1)
    """
    return side_m15 in ("LONG", "SHORT") and bool(anti_chase_ok) and bool(snapshot_ok)


def should_promote_probe(*, m15_h1_ok: bool, score_ok: bool, regime_ok: bool) -> bool:
    """
    Promote probe -> full khi:
      - M15 & H1 đồng hướng
      - điểm M15/H1 đạt ngưỡng hiệu lực
      - regime ∈ {NORMAL, STRONG}
    """
    return bool(m15_h1_ok) and bool(score_ok) and bool(regime_ok)


# =========================
# 3) TIME-BASED EXIT
# =========================
def time_based_probe_exit(trade: Dict[str, Any], *, max_minutes: int = 20, now_ts: Optional[int] = None) -> bool:
    """
    Đóng probe nếu "rề rà": mở quá 'max_minutes' mà chưa promote.
    - Trade cần có 'created_ts' (epoch). Nếu không có, bỏ qua.
    """
    try:
        if not trade or trade.get("size_type") != "PROBE":
            return False
        created = float(trade.get("created_ts"))
        now_ts = float(now_ts or time.time())
        return (now_ts - created) >= (max_minutes * 60.0)
    except Exception:
        return False


# =========================
# 4) ABSORPTION PAUSE GUARD
# =========================
_absorption_pause_until_ts: Dict[str, float] = {}

def absorption_pause_guard(symbol: str, indicators_m15: Dict[str, Any], *,
                           wick_absorb_thresh: float = 1.8,
                           cool_down_sec: int = 60) -> bool:
    """
    Phát hiện wick hấp thụ lớn ở nến gần nhất → tạm ngưng mở lệnh trong 'cool_down_sec'.
    - Wick ratio tính thô: max(upper_wick, lower_wick)/max(1e-9, body)
    - Nếu lớn > 'wick_absorb_thresh' → ghi 'pause_until' cho symbol.
    Trả về True nếu đang trong thời gian pause (nghĩa là NÊN BỎ QUA ENTRY hiện tại).
    """
    now = time.time()
    key = str(symbol).upper()

    # Nếu đang trong pause window → chặn
    until = _absorption_pause_until_ts.get(key, 0.0)
    if now < until:
        return True

    try:
        # Lấy body/upper/lower wick của nến cuối
        def _last(col):
            s = indicators_m15.get(col)
            if hasattr(s, "iloc"): return float(s.iloc[-1])
            if isinstance(s, (list, tuple)) and s: return float(s[-1])
            return float(s or 0.0)

        body  = abs(_last("body"))
        uwick = abs(_last("upper_wick"))
        lwick = abs(_last("lower_wick"))
        wick_ratio = max(uwick, lwick) / max(body, 1e-9)

        if wick_ratio >= float(wick_absorb_thresh):
            _absorption_pause_until_ts[key] = now + float(cool_down_sec)
            return True
    except Exception:
        # nếu không tính được → không pause
        return False

    return False


# =========================
# 5) PARTIAL TP & TRAILING
# =========================
def partial_take_profit(trade: Dict[str, Any], last_price: float, *,
                        atr: float, tp1_mult: float = 0.8, tp2_mult: float = 1.6) -> Tuple[int, Optional[str]]:
    """
    Gợi ý chốt 2 nấc theo ATR bands:
      - TP1 = entry ± tp1_mult*ATR (30–40%)
      - TP2 = entry ± tp2_mult*ATR (30–40%)
    Trả về (nấc đạt được: 0/1/2, note).
    """
    try:
        direction = trade.get("direction")
        entry = float(trade.get("entry"))
        atr = float(atr)
        tp1 = entry + (tp1_mult * atr if direction == "LONG" else -tp1_mult * atr)
        tp2 = entry + (tp2_mult * atr if direction == "LONG" else -tp2_mult * atr)

        if direction == "LONG":
            if last_price >= tp2: return 2, f"TP2 @{tp2:.4f}"
            if last_price >= tp1: return 1, f"TP1 @{tp1:.4f}"
        elif direction == "SHORT":
            if last_price <= tp2: return 2, f"TP2 @{tp2:.4f}"
            if last_price <= tp1: return 1, f"TP1 @{tp1:.4f}"
    except Exception:
        pass
    return 0, None


def trailing_by_atr(trade: Dict[str, Any], last_price: float, atr: float,
                    mult: float = 1.2) -> Optional[float]:
    """
    Gợi ý SL mới theo ATR. Trả về SL mới (float) hoặc None (không thay đổi).
    - LONG: SL đề xuất = max(SL cũ, last_price - mult*ATR)
    - SHORT: SL đề xuất = min(SL cũ, last_price + mult*ATR)
    """
    try:
        direction = trade.get("direction")
        old_sl = float(trade.get("sl"))
        if direction == "LONG":
            new_sl = max(old_sl, float(last_price) - float(mult) * float(atr))
            return new_sl if new_sl > old_sl else None
        elif direction == "SHORT":
            new_sl = min(old_sl, float(last_price) + float(mult) * float(atr))
            return new_sl if new_sl < old_sl else None
    except Exception:
        return None
    return None


def manage_trailing_and_partial(trade: Dict[str, Any], last_price: float, *,
                                atr: float,
                                enable_trailing: bool = True,
                                trailing_mult: float = 1.2) -> Dict[str, Any]:
    """
    Helper tổng: xét partial TP (2 nấc) + trailing ATR. Trả về dict kết quả gợi ý.
    """
    result = {"tp_level": 0, "tp_note": None, "new_sl": None}
    tp_level, note = partial_take_profit(trade, last_price, atr=atr)
    result.update({"tp_level": tp_level, "tp_note": note})
    if enable_trailing:
        new_sl = trailing_by_atr(trade, last_price, atr, mult=trailing_mult)
        result["new_sl"] = new_sl
    return result
