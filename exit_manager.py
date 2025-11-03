from __future__ import annotations
import time
from typing import Dict, Any

def _safe_float(x, d=0.0):
    try: return float(x)
    except Exception: return float(d)

def _last(series, default=0.0):
    try:
        if hasattr(series, "iloc"): return float(series.iloc[-1])
        return float(series)
    except Exception: return float(default)

class ExitManager:
    def __init__(self, cfg: dict = None):
        self.cfg = cfg or {}
        self.monitor = SignalMonitor(cfg)

    def maybe_manage_exit_trend(self, ctx: Dict[str, Any]):
        m15 = (ctx["indicators"].get("M15") or {})
        adx = _last(m15.get("adx")); bbw = _last(m15.get("bbw")); rsi = _last(m15.get("rsi"))
        side = ctx.get("decision", ("FLAT",0))[0]; symbol = ctx.get("symbol","")
        adx_th = float((self.cfg.get("exit") or {}).get("trend_adx_min", 15))
        bbw_th = float((self.cfg.get("exit") or {}).get("trend_bbw_min", 0.12))
        if adx < adx_th and bbw < bbw_th:
            msg = f"[EXIT_TREND] {symbol}: ADX={adx:.2f} < {adx_th}, BBW={bbw:.3f} < {bbw_th}"
            if ctx.get("notifier"): ctx["notifier"].vfi_exit(symbol, side, msg)
            if ctx.get("logger"): ctx["logger"].log_trade_event(ctx, event="EXIT_TREND", pos={}, reason=msg)
            if ctx.get("trade_sim"): ctx["trade_sim"].close(ctx, {"symbol":symbol,"side":side,"qty":0}, exit_reason="TREND_WEAK")

    def manage_sideway_exit(self, ctx: Dict[str, Any]):
        m15 = (ctx["indicators"].get("M15") or {})
        bbw = _last(m15.get("bbw")); adx = _last(m15.get("adx")); rsi = _last(m15.get("rsi"))
        side = ctx.get("decision", ("FLAT",0))[0]; symbol = ctx.get("symbol","")
        if bbw < 0.09 and adx < 12 and 45 <= rsi <= 55:
            msg = f"[EXIT_SIDEWAY] {symbol}: BBW={bbw:.3f}, ADX={adx:.2f}, RSI={rsi:.1f}"
            if ctx.get("notifier"): ctx["notifier"].vfi_exit(symbol, side, msg)
            if ctx.get("logger"): ctx["logger"].log_trade_event(ctx, event="EXIT_SIDEWAY", pos={}, reason=msg)
            if ctx.get("trade_sim"): ctx["trade_sim"].close(ctx, {"symbol":symbol,"side":side,"qty":0}, exit_reason="SIDEWAY_CONGESTION")

    def manage_transition_exit(self, ctx: Dict[str, Any]):
        h1 = (ctx["indicators"].get("H1") or {})
        ema21 = _last(h1.get("ema21")); ema50 = _last(h1.get("ema50")); adx = _last(h1.get("adx"))
        side = ctx.get("decision", ("FLAT",0))[0]; symbol = ctx.get("symbol","")
        ema_slope = (ema21 - ema50); adx_th = float((self.cfg.get("exit") or {}).get("transition_adx_drop", 14))
        if adx < adx_th and abs(ema_slope) < 0.001:
            msg = f"[EXIT_TRANSITION] {symbol}: ADX={adx:.1f} < {adx_th}, EMA slope≈0"
            if ctx.get("notifier"): ctx["notifier"].vfi_exit(symbol, side, msg)
            if ctx.get("logger"): ctx["logger"].log_trade_event(ctx, event="EXIT_TRANSITION", pos={}, reason=msg)
            if ctx.get("trade_sim"): ctx["trade_sim"].close(ctx, {"symbol":symbol,"side":side,"qty":0}, exit_reason="TRANSITION_PHASE")

    def check_all(self, ctx: Dict[str, Any]):
        self.monitor.update(ctx)
        self.maybe_manage_exit_trend(ctx)
        self.manage_sideway_exit(ctx)
        self.manage_transition_exit(ctx)

class SignalMonitor:
    def __init__(self, cfg: dict = None):
        self.cfg = cfg or {}
        self.active_signals: Dict[str, dict] = {}

    def update(self, ctx: Dict[str, Any]):
        symbol = ctx.get("symbol","")
        side, conf = ctx.get("decision", ("FLAT",0))
        conf = float(conf)
        vfi_flow = float(ctx.get("vfi_flow",0))
        entry = self.active_signals.get(symbol)
        now = int(time.time())

        if not entry and side in ("LONG","SHORT") and conf > 0.05:
            self.active_signals[symbol] = {"side": side, "opened": now, "peak_score": conf, "flow": vfi_flow}
            return

        if entry:
            entry["peak_score"] = max(entry["peak_score"], conf)
            score_drop = entry["peak_score"] - conf
            weak_threshold = float((self.cfg.get("monitor") or {}).get("weak_drop_threshold", 0.25))

            if score_drop >= weak_threshold:
                msg = f"[MONITOR_WEAK] {symbol}: score_drop={score_drop:.2f}, flow={vfi_flow:.2f}"
                if ctx.get("notifier"): ctx["notifier"].vfi_exit(symbol, side, msg)
                if ctx.get("logger"): ctx["logger"].log_trade_event(ctx, event="MONITOR_WEAK", pos={}, reason=msg)
                if ctx.get("trade_sim"): ctx["trade_sim"].close(ctx, {"symbol":symbol,"side":side,"qty":0}, exit_reason="SCORE_WEAK")
                self.active_signals.pop(symbol, None)
                return

            if side == "FLAT":
                self.active_signals.pop(symbol, None)
