# order_manager.py — regime-aware trade manager with VFI exit guard
from __future__ import annotations
from typing import Dict, Any, Optional
import time

from vfi_module import calc_vfi_features, vfi_exit_signal

class OrderManager:
    def __init__(self):
        self.position: Optional[Dict[str,Any]] = None  # {"symbol","side","qty","entry","sl","tp","vfi_prev_feats",...}

    def _atr(self, ctx: Dict[str, Any]) -> float:
        try:
            return float(ctx["indicators"].get("H1", {}).get("atr", 0.0) or 0.0)
        except Exception:
            return 0.0

    def open_if_ok(self, ctx: Dict[str, Any], side: str) -> bool:
        if self.position:
            return False
        symbol = ctx["symbol"]
        atr = self._atr(ctx) or 0.0
        price = float(ctx["indicators"].get("M15", {}).get("close", 0.0) or 0.0)
        if price <= 0:
            return False
        risk = ctx["cfg"].get("risk", {})
        qty = max(1.0, float(risk.get("min_notional", 5)) / max(price, 1e-9))
        sl_atr_mult = 1.5
        sl = price - sl_atr_mult*atr if side=="LONG" else price + sl_atr_mult*atr
        tp = price + 1.5*sl_atr_mult*atr if side=="LONG" else price - 1.5*sl_atr_mult*atr
        self.position = {"symbol": symbol, "side": side, "qty": qty, "entry": price, "sl": sl, "tp": tp, "opened_at": int(time.time())}
        if ctx.get("logger"):
            ctx["logger"].log_trade_event(ctx, event="OPEN", pos=self.position, reason="MGV_OPEN")
        if ctx.get("trade_sim"):
            ctx["trade_sim"].open(ctx, self.position)
        return True

    def _reduce_or_close(self, ctx: Dict[str,Any], reduce_frac: float, reason: str):
        if not self.position or not self.position.get("qty",0)>0:
            return
        pos = self.position
        symbol = pos["symbol"]
        if reduce_frac >= 0.99:
            if ctx.get("trade_sim"):
                ctx["trade_sim"].close(ctx, pos, exit_reason=reason)
            if ctx.get("logger"):
                ctx["logger"].log_trade_event(ctx, event="CLOSE", pos=pos, reason=reason)
            self.position = None
        else:
            reduce_qty = pos["qty"] * float(reduce_frac)
            pos["qty"] -= reduce_qty
            if ctx.get("trade_sim"):
                ctx["trade_sim"].reduce(ctx, pos, reduce_qty, reason=reason)
            if ctx.get("logger"):
                ctx["logger"].log_trade_event(ctx, event="REDUCE", pos=pos, reason=reason)

    def _apply_trailing(self, ctx: Dict[str,Any]):
        if not self.position:
            return
        p = self.position
        atr = self._atr(ctx)
        price = float(ctx["indicators"].get("M15", {}).get("close", 0.0) or 0.0)
        trail_mult = 1.0
        if p["side"]=="LONG":
            p["sl"] = max(p["sl"], price - trail_mult*atr)
        else:
            p["sl"] = min(p["sl"], price + trail_mult*atr)

    def manage(self, ctx: Dict[str, Any]):
        # trailing
        self._apply_trailing(ctx)

        # --- VFI EXIT GUARD -------------------------------------------------
        if self.position and self.position.get("qty",0)>0:
            try:
                vfi_cfg = (ctx["cfg"].get("vfi") or {}).get("exit", {})
                wick_th = float(vfi_cfg.get("wick_threshold", 0.8))
                m15 = ctx["indicators"].get("M15", {}).get("df")
                if m15 is not None and len(getattr(m15, "index", [])) >= 30:
                    feats_now = calc_vfi_features(
                        m15,
                        vwap=ctx["indicators"].get("M15", {}).get("vwap"),
                        atr=ctx["indicators"].get("M15", {}).get("atr")
                    )
                    prev_feats = self.position.get("vfi_prev_feats") or {}
                    exit_reason = vfi_exit_signal(prev_feats, feats_now, self.position["side"], wick_th)
                    self.position["vfi_prev_feats"] = feats_now
                    if exit_reason:
                        if ctx.get("logger"):
                            ctx["logger"].log_trade_event(ctx, event="VFI_EXIT", pos=self.position, reason=exit_reason)
                        # reduce half trước; phần còn lại để trailing/TP xử lý
                        self._reduce_or_close(ctx, 0.5, exit_reason)
            except Exception as e:
                if ctx.get("logger"):
                    ctx["logger"].log_trade_event(ctx, event="VFI_EXIT_ERROR", pos=self.position or {}, reason=str(e))
        # -------------------------------------------------------------------

    def close_all(self, ctx: Dict[str, Any], reason: str="FORCE_CLOSE") -> None:
        if not self.position:
            return
        if ctx.get("trade_sim"):
            ctx["trade_sim"].close(ctx, self.position, exit_reason=reason)
        if ctx.get("logger"):
            ctx["logger"].log_trade_event(ctx, event="CLOSE", pos=self.position, reason=reason)
        self.position=None
