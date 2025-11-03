# trade_simulator.py — FINAL (paper-trade)
from __future__ import annotations

class PaperTrader:
    def __init__(self, cfg=None):
        self.cfg = cfg or {}

    def open(self, ctx, pos):
        ntf = ctx.get("notifier")
        if ntf: ntf.trade_open(pos.get("symbol",""), pos.get("side",""), pos.get("qty",0), pos.get("entry",""))

    def reduce(self, ctx, pos, reduce_qty, reason=''):
        ntf = ctx.get("notifier")
        if ntf: ntf.trade_reduce(pos.get("symbol",""), pos.get("side",""), reduce_qty, ctx.get("price",0.0), reason)

    def close(self, ctx, pos, exit_reason=''):
        ntf = ctx.get("notifier")
        if ntf: ntf.trade_close(pos.get("symbol",""), pos.get("side",""), pos.get("qty",0), ctx.get("price",0.0), exit_reason)
