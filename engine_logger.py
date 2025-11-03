# engine_logger.py — FINAL
from __future__ import annotations
import csv, os, time
from typing import Any, Dict, Optional

class EngineLogger:
    def __init__(self, cfg: Dict[str, Any] | None = None):
        self.cfg = cfg or {}
        logcfg = (self.cfg.get("logging") or {})
        base_dir = "."

        self.fp_votes   = os.path.join(base_dir, logcfg.get("votes_path", "votes.csv"))
        self.fp_entries = os.path.join(base_dir, logcfg.get("entries_reason_path", "entries_reason.csv"))
        self.fp_trades  = os.path.join(base_dir, logcfg.get("trades_log", "trades_log.csv"))
        self.fp_cycles  = os.path.join(base_dir, logcfg.get("cycles_path", "cycles_log.csv"))

        self._ensure(self.fp_entries, [
            "ts","symbol","regime","macro_bias","side",
            "reason","price","group_scores","extra_json"
        ])
        self._ensure(self.fp_trades, [
            "ts","event","symbol","regime","side",
            "entry","sl","tp1","tp2","price_at_event",
            "exit_reason","qty","tp1_hit","pnl_est_r"
        ])
        self._ensure(self.fp_votes, [
            "ts","symbol","regime","trend","momentum","mean","flow",
            "score","side","details_json"
        ])
        self._ensure(self.fp_cycles, [
            "ts","symbol","status","side","conf","vfi_flow","vfi_long","vfi_short","latency_sec"
        ])

    def _ensure(self, path: str, headers):
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            with open(path, "w", newline="") as f:
                csv.writer(f).writerow(headers)

    @staticmethod
    def _now() -> int:
        return int(time.time())

    @staticmethod
    def _json(obj: Any) -> str:
        import json
        try: return json.dumps(obj, ensure_ascii=False, separators=(",",":"))
        except Exception: return ""

    def log_entry_reason(self, ctx: Dict[str,Any], reason: str, extra: Optional[Dict[str,Any]]=None):
        row = [
            self._now(),
            ctx.get("symbol",""),
            ctx.get("regime",""),
            ctx.get("macro_bias",""),
            ctx.get("side",""),
            reason or "",
            float(ctx.get("price",0.0) or 0.0),
            self._json(ctx.get("group_scores", {})),
            self._json(extra or {}),
        ]
        with open(self.fp_entries, "a", newline="") as f:
            csv.writer(f).writerow(row)

    def log_trade_event(self, ctx: Dict[str,Any], event: str, pos: Optional[Dict[str,Any]]=None, reason: Optional[str]=None, pnl_est_r: Optional[float]=None):
        p = pos or {}
        row = [
            self._now(),
            event,
            ctx.get("symbol",""),
            p.get("regime", ctx.get("regime","")),
            p.get("side",  ctx.get("side","")),
            p.get("entry",""),
            p.get("sl",""),
            p.get("tp1",""),
            p.get("tp2",""),
            float(ctx.get("price",0.0) or 0.0),
            reason or "",
            p.get("qty",""),
            p.get("tp1_hit",""),
            "" if pnl_est_r is None else float(pnl_est_r),
        ]
        with open(self.fp_trades, "a", newline="") as f:
            csv.writer(f).writerow(row)

    def log_vote_snapshot(self, payload: Dict[str,Any]):
        row = [
            self._now(),
            payload.get("symbol",""),
            payload.get("regime",""),
            float(payload.get("trend",0.0)),
            float(payload.get("momentum",0.0)),
            float(payload.get("mean",0.0)),
            float(payload.get("flow",0.0)),
            float(payload.get("score",0.0)),
            payload.get("side",""),
            self._json(payload.get("details", {})),
        ]
        with open(self.fp_votes, "a", newline="") as f:
            csv.writer(f).writerow(row)

    def log_cycle(self, r: Dict[str,Any]):
        row = [
            self._now(),
            r.get("symbol",""),
            r.get("status",""),
            (r.get("decision") or ("FLAT",0.0))[0],
            float((r.get("decision") or ("FLAT",0.0))[1]),
            float(r.get("vfi_flow",0.0)),
            float((r.get("vfi_scores") or {}).get("long",0.0)),
            float((r.get("vfi_scores") or {}).get("short",0.0)),
            float(r.get("latency_sec",0.0)),
        ]
        with open(self.fp_cycles, "a", newline="") as f:
            csv.writer(f).writerow(row)
