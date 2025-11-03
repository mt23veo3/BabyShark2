# signal_manager.py — FINAL
# -------------------------------------------------------
# - Đóng vai trò publisher và đồng bộ với EngineLogger
# - Hỗ trợ queue background để tránh chặn I/O
# - Có thể bật dashboard push (HTTP POST)
# - Gọi EngineLogger để ghi CSV thống nhất
from __future__ import annotations
import csv, os, time, json, threading, queue
from typing import Dict, Any

try:
    from urllib import request as _urlreq
except Exception:
    _urlreq = None

class SignalManager:
    def __init__(self, cfg: dict = None, engine_logger=None):
        self.cfg = cfg or {}
        self.logger = engine_logger
        logcfg = (self.cfg.get("logging") or {})
        self.enabled = True
        self.q: "queue.Queue[Dict[str,Any]]" = queue.Queue(maxsize=10000)
        self._stop = threading.Event()
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    # ---------- background ----------
    def stop(self):
        self._stop.set()
        try:
            self.worker.join(timeout=1.5)
        except Exception:
            pass

    def _run(self):
        while not self._stop.is_set():
            try:
                msg = self.q.get(timeout=0.2)
            except Exception:
                continue
            try:
                t = msg.get("type")
                if t == "score":
                    self._handle_score(msg)
                elif t == "signal":
                    self._handle_signal(msg)
                elif t == "vote":
                    self._handle_vote(msg)
            except Exception:
                pass

    # ---------- public methods ----------
    def write_score(self, result: dict, tf: str, total_score: float, ages: dict, exit_reason: str = ""):
        msg = {"type": "score", "result": result, "tf": tf, "total_score": total_score, "ages": ages, "exit_reason": exit_reason}
        self.q.put_nowait(msg)

    def write_signal(self, symbol: str, side: str, reason: str, vfi: dict):
        msg = {"type": "signal", "symbol": symbol, "side": side, "reason": reason, "vfi": vfi}
        self.q.put_nowait(msg)

    def write_vote(self, symbol: str, groups: dict, decision: tuple, ok: bool = True):
        msg = {"type": "vote", "symbol": symbol, "groups": groups, "decision": decision, "ok": ok}
        self.q.put_nowait(msg)

    # ---------- handlers ----------
    def _handle_score(self, msg: dict):
        result, tf, total_score, ages, exit_reason = (
            msg["result"], msg["tf"], msg["total_score"], msg.get("ages") or {}, msg.get("exit_reason","")
        )
        if self.logger:
            self.logger.log_score(result, tf, total_score, ages, exit_reason)
        self._dashboard_emit({
            "symbol": result.get("symbol",""),
            "tf": tf,
            "score": total_score,
            "vfi": result.get("vfi_scores",{}),
            "flow": result.get("vfi_flow",0.0),
            "ages": ages,
            "exit_reason": exit_reason
        })

    def _handle_signal(self, msg: dict):
        if self.logger:
            self.logger.log_signal(msg["symbol"], msg["side"], msg["reason"], msg.get("vfi",{}) or {})
        self._dashboard_emit({
            "symbol": msg["symbol"],
            "side": msg["side"],
            "reason": msg["reason"],
            "vfi": msg.get("vfi",{})
        })

    def _handle_vote(self, msg: dict):
        if self.logger:
            self.logger.log_vote(msg["symbol"], msg["groups"], msg["decision"], msg.get("ok",True))
        self._dashboard_emit({
            "symbol": msg["symbol"],
            "vote": msg["decision"],
            "groups": msg["groups"],
            "ok": msg.get("ok",True)
        })

    # ---------- dashboard ----------
    def _dashboard_emit(self, payload: dict):
        dash = (self.cfg.get("dashboard") or {})
        if not bool(dash.get("enabled", False)):
            return
        ep = dash.get("endpoint")
        if not ep or _urlreq is None:
            return
        try:
            data = json.dumps(payload).encode("utf-8")
            req = _urlreq.Request(ep, data=data, headers={"Content-Type":"application/json"})
            _urlreq.urlopen(req, timeout=1.5)
        except Exception:
            pass

