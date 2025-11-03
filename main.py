# main.py — FINAL (anti-spam Discord)
from __future__ import annotations
import asyncio, json, os, signal, time, traceback
from typing import Dict, Any

from data import build_exchange, DataFeed
from engine_flow import engine_loop
from trade_simulator import PaperTrader
from notifier import Notifier
from signal_manager import SignalManager
from engine_logger import EngineLogger
from exit_manager import ExitManager


def log(msg: str):
    print(msg, flush=True)


def load_config(path: str = "config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _deep_merge(a: dict, b: dict) -> dict:
    if not isinstance(a, dict) or not isinstance(b, dict):
        return b if b is not None else a
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = _deep_merge(out[k], v) if (k in out and isinstance(out[k], dict) and isinstance(v, dict)) else v
    return out


def resolve_profile(cfg_raw: dict) -> dict:
    cfg = dict(cfg_raw or {})
    prof = cfg.get("profiles") or {}
    act = cfg.get("active_profile")
    if act and act in prof:
        cfg = _deep_merge(cfg, prof[act])
    return cfg


class StopEvent:
    def __init__(self):
        self._flag = False
    def is_set(self):
        return self._flag
    def set(self):
        self._flag = True


def install_signal_handlers(stop: StopEvent):
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            signal.signal(sig, lambda *_: stop.set())


def _as_decision(x):
    """Chuẩn hoá mọi kiểu decision về (SIDE, CONF)."""
    if isinstance(x, (list, tuple)):
        if len(x) >= 2:
            return str(x[0]).upper(), float(x[1])
        if len(x) == 1:
            return str(x[0]).upper(), 0.0
    if isinstance(x, dict):
        side = x.get("side", "NEUTRAL")
        conf = x.get("confidence", x.get("score", 0.0))
        return str(side).upper(), float(conf)
    return "NEUTRAL", 0.0


class CycleCSV:
    def __init__(self, path: str = "cycles_log.csv"):
        self.path = path
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                f.write("ts,symbol,status,side,conf,vfi_flow,vfi_long,vfi_short,latency_sec\n")

    def write(self, r: Dict[str, Any]):
        ts = int(time.time())
        side, conf = _as_decision(r.get("decision", ("FLAT", 0.0)))
        vfi = r.get("vfi_scores", {}) or {}
        row = [
            str(ts),
            str(r.get("symbol", "")),
            str(r.get("status", "")),
            str(side),
            f"{float(conf):.4f}",
            f"{float(r.get('vfi_flow', 0.0)):.4f}",
            f"{float(vfi.get('long', 0.0)):.2f}",
            f"{float(vfi.get('short', 0.0)):.2f}",
            str(r.get("latency_sec", 0.0)),
        ]
        with open(self.path, "a") as f:
            f.write(",".join(row) + "\n")


# --- chống spam notify: chỉ gửi khi có thay đổi ---
_last_decision_cache: Dict[str, tuple] = {}


async def run_once(cfg: dict, data_feed: DataFeed, state: dict, cycles_csv: CycleCSV):
    symbols = cfg.get("symbols") or ["BTC/USDT"]
    results = await engine_loop(symbols, data_feed, cfg, state)
    for r in (results or []):
        if isinstance(r, Exception):
            log(f"[ERROR] symbol task error: {r}")
            if state.get("notifier"):
                state["notifier"].error(f"symbol task error: {r}")
            continue

        # ghi CSV chu kỳ
        cycles_csv.write(r)

        # notify có điều kiện (anti-spam)
        ntf = state.get("notifier")
        if ntf and cfg.get("notifier", {}).get("notify_decision", False):
            sym = r.get("symbol", "")
            side, conf = _as_decision(r.get("decision", ("FLAT", 0.0)))
            flow = float(r.get("vfi_flow", 0.0))
            cur_key = (side, round(conf, 2), round(flow, 2))
            if _last_decision_cache.get(sym) != cur_key:
                _last_decision_cache[sym] = cur_key
                ntf.decision(sym, side, float(conf), flow)

        # ghi thêm vào logger nếu có
        if state.get("engine_logger"):
            state["engine_logger"].log_cycle(r)


async def main():
    cfg_raw = load_config("config.json")
    cfg = resolve_profile(cfg_raw)
    interval = int(cfg.get("interval_sec", cfg_raw.get("interval_sec", 60)))
    log(f"[BOOT] BabyShark | active_profile={cfg_raw.get('active_profile', '(none)')} | interval={interval}s")

    try:
        exchange = build_exchange(cfg)
    except Exception as e:
        log(f"[FATAL] build_exchange error: {e}")
        return

    data_feed = DataFeed(exchange, cfg, logger=None)

    trade_sim = PaperTrader(cfg)
    notifier = Notifier(cfg)
    notifier.ping("Boot OK | profile=%s" % cfg_raw.get("active_profile", "default"))
    englog = EngineLogger(cfg)
    exitman = ExitManager(cfg)
    sigman = SignalManager(cfg, engine_logger=englog)

    state = {
        "trade_sim": trade_sim,
        "notifier": notifier,
        "engine_logger": englog,
        "signal_manager": sigman,
        "exit_manager": exitman,
    }

    cycles_csv = CycleCSV(cfg.get("logging", {}).get("cycles_path", "cycles_log.csv"))
    stop = StopEvent()
    install_signal_handlers(stop)

    timeout = max(15, interval * 2)
    backoff = 1.0

    while not stop.is_set():
        started = time.time()
        try:
            await asyncio.wait_for(run_once(cfg, data_feed, state, cycles_csv), timeout=timeout)
            backoff = 1.0
        except asyncio.TimeoutError:
            log("[WARN] run_once timeout; continue.")
        except Exception:
            log(f"[ERROR] main loop:\n{traceback.format_exc()}")
            await asyncio.sleep(min(30.0, backoff))
            backoff = min(30.0, backoff + 2.0)
        elapsed = time.time() - started
        await asyncio.sleep(max(0.0, interval - elapsed))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting…")
