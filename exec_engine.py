# exec_engine.py
from __future__ import annotations
from typing import Optional
import time

class ExecEngine:
    """
    Bao quanh TradeSimulator để:
    - mở lệnh probe/full
    - promote probe -> full
    - đóng lệnh
    Đồng thời cập nhật TradeState để main/trend/sideway chỉ gọi một chỗ.
    """
    def __init__(self, simulator, notifier, state):
        self.sim = simulator
        self.notifier = notifier
        self.state = state

    def open_probe(
        self,
        symbol: str,
        direction: str,
        price_now: float,
        now_epoch: float,
        *,
        size_quote: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        **extra
    ):
        """
        Map sang simulator.open_trade(...):
        - dùng tham số keyword cho tương thích code hiện có trong main.py
        """
        trade = self.sim.open_trade(
            symbol, direction,
            entry=price_now, sl=sl, tp=tp,
            size_quote=size_quote,
            is_probe=True,
            now_ts=now_epoch,
            **extra
        )
        self.state.set_probe(trade)
        return trade

    def open_full(
        self,
        symbol: str,
        direction: str,
        price_now: float,
        now_epoch: float,
        *,
        size_quote: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        **extra
    ):
        trade = self.sim.open_trade(
            symbol, direction,
            entry=price_now, sl=sl, tp=tp,
            size_quote=size_quote,
            is_probe=False,
            now_ts=now_epoch,
            **extra
        )
        # mở thẳng full thì ghi luôn active_full
        self.state.promote_to_full(symbol, trade)
        return trade

    def promote_full(
        self,
        symbol: str,
        promote_size_quote: float,
        price_now: float,
        now_epoch: float,
        **extra
    ):
        probe, _full = self.state.get_active(symbol)
        if not probe:
            return None
        # simulator.promote_trade(trade, add_notional, price_now, now_ts=None)
        trade = self.sim.promote_trade(probe, promote_size_quote, price_now, now_ts=now_epoch)
        # simulator trả về lệnh full; cập nhật state
        self.state.promote_to_full(symbol, trade)
        return trade

    def close(
        self,
        symbol: str,
        price_now: float,
        status_tag: str,
        now_epoch: float,
        reason: str = "",
        prefer_full: bool = True
    ):
        probe, full = self.state.get_active(symbol)
        target = full if (prefer_full and full) else (probe or full)
        if not target:
            return None
        closed = self.sim.close_trade(target, price_now, status_tag, now_ts=now_epoch, reason=reason)
        # clear state + lưu thời gian đóng gần nhất
        self.state.clear_symbol(symbol)
        self.state.last_close_time[symbol] = time.time()
        return closed
