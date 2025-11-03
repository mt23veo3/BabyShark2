# trade_state.py
from __future__ import annotations
from typing import Optional, Dict

class TradeState:
    """
    Lưu trạng thái lệnh theo symbol để đọc/ghi tập trung,
    loại bỏ hoàn toàn việc dùng biến local active_probe/active_full rải rác.
    """
    def __init__(self) -> None:
        self.active_probe: Dict[str, dict] = {}
        self.active_full: Dict[str, dict] = {}
        self.last_trade: Dict[str, dict] = {}
        self.last_close_time: Dict[str, float] = {}
        self.sent_side: Dict[str, float] = {}  # nếu main dùng throttle SENT_SIDE

    def get_active(self, symbol: str) -> tuple[Optional[dict], Optional[dict]]:
        return self.active_probe.get(symbol), self.active_full.get(symbol)

    def set_probe(self, trade: dict) -> None:
        if not trade:
            return
        sym = trade.get("symbol")
        if sym:
            self.active_probe[sym] = trade

    def promote_to_full(self, symbol: str, full_trade: dict) -> None:
        if not symbol or not full_trade:
            return
        # chuyển probe -> full
        self.active_full[symbol] = full_trade
        if symbol in self.active_probe:
            del self.active_probe[symbol]

    def clear_symbol(self, symbol: str) -> None:
        self.active_probe.pop(symbol, None)
        self.active_full.pop(symbol, None)
