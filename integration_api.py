# -*- coding: utf-8 -*-
import time
from typing import Dict, Optional

import pandas as pd

from indicators import calculate_indicators
from votes import tally_votes
from tight_gate import (
    StablePassTracker,
    CooldownManager,
    anti_chase_ok,
    build_indicator_results,
    _heavy_hits,
)
from order_planner import plan_probe_and_topup
from exec_engine import ExecutionEngine

class SharkEngineFacade:
    def __init__(self, cfg: Dict):
        self.cfg = cfg or {}
        self.eng = ExecutionEngine(cfg)
        self.stable = StablePassTracker(
            path=(self.cfg.get("tight_mode") or {}).get("state_path", "tight_state.json"),
            min_gap_sec=int((self.cfg.get("tight_mode") or {}).get("snapshot_min_gap_sec", 300)),
            required_passes=int((self.cfg.get("tight_mode") or {}).get("snapshot_confirmations", 2)),
        )
        self.cd = CooldownManager(path=(self.cfg.get("tight_mode") or {}).get("cooldown_path", "tight_cooldown.json"))

        self.th_m15 = float((self.cfg.get("thresholds") or {}).get("M15", self.cfg.get("score_threshold", 17.0)))
        self.adx_h1_th = int(self.cfg.get("adx_h1_threshold", 25))
        self.anti_mult = float((self.cfg.get("tight_mode") or {}).get("anti_chase_atr_mult", 0.5))
        self.cooldown_min = int((self.cfg.get("tight_mode") or {}).get("cooldown_m15_min", 15))
        self.heavy_required = int((self.cfg.get("tight_mode") or {}).get("heavy_required", 3))

        self.wsets = (self.cfg or {}).get("weights_sets", {})
        self.w_m15 = self.wsets.get("M15", {})
        self.w_h1 = self.wsets.get("H1", {})

    @staticmethod
    def _decide_side(score_long: float, score_short: float, eps: float = 0.1) -> str:
        if score_long - score_short > eps:
            return "LONG"
        if score_short - score_long > eps:
            return "SHORT"
        return "NEUTRAL"

    def process_intrabar(
        self,
        symbol: str,
        m5: pd.DataFrame,
        m15: pd.DataFrame,
        h1: pd.DataFrame,
        d1: pd.DataFrame,  # <--- Nhận thêm D1
        now_ts: Optional[float] = None,
        config: Optional[Dict] = None,
    ) -> Dict:
        if now_ts is None:
            now_ts = time.time()
        if config is None:
            config = self.cfg

        timeframe = "15m"
        if m15 is None or m15.empty or h1 is None or h1.empty or m5 is None or m5.empty:
            return {"entry_ready": False, "blocked_by": ["No data"], "actions": []}

        ind_m15 = calculate_indicators(m15, config, timeframe="15m")
        ind_h1 = calculate_indicators(h1, config, timeframe="1h")
        ind_d1 = calculate_indicators(d1, config, timeframe="1d") if d1 is not None and not d1.empty else None  # <--- Tính trend D1

        map_m15 = build_indicator_results(m15, ind_m15)
        vr_m15 = tally_votes(map_m15, self.w_m15)
        sl15, ss15 = float(vr_m15.get("score_long", 0)), float(vr_m15.get("score_short", 0))
        side = self._decide_side(sl15, ss15)

        adx_h1 = float(ind_h1["adx"].iloc[-1])
        hh1 = _heavy_hits(build_indicator_results(h1, ind_h1), ind_h1["ema200"], side) if side != "NEUTRAL" else 0
        h1_ok = (adx_h1 >= self.adx_h1_th) and (hh1 >= self.heavy_required) and (side != "NEUTRAL")
        m15_score = sl15 if side == "LONG" else (ss15 if side == "SHORT" else 0.0)
        m15_ok = (side != "NEUTRAL") and (m15_score >= self.th_m15)
        ac_ok, c, v, a = anti_chase_ok(m15, ind_m15, mult=self.anti_mult)

        gates_ok = h1_ok and m15_ok and ac_ok and (side != "NEUTRAL")

        is_stable = self.stable.update(symbol, timeframe, side, gates_ok, now_ts=now_ts)
        in_cooldown = self.cd.in_cooldown(symbol, timeframe, cooldown_sec=self.cooldown_min * 60, now_ts=now_ts)

        last_price = float(m5["close"].iloc[-1])

        entry_ready = gates_ok and is_stable and not in_cooldown

        blocked_by = []
        if not h1_ok:
            blocked_by.append("H1 gate")
        if not m15_ok:
            blocked_by.append("M15 score")
        if not ac_ok:
            blocked_by.append("Anti-chase")
        if side == "NEUTRAL":
            blocked_by.append("Side neutral")
        if in_cooldown:
            blocked_by.append("Cooldown")
        if not is_stable:
            blocked_by.append("Not stable 2×M5")

        entry_signal = None
        actions = []
        if entry_ready:
            plan = plan_probe_and_topup(side, m15, ind_m15, config)
            s1 = self.eng.tick(symbol, timeframe, side, plan, last_price, ts_now=now_ts)
            actions.extend(s1.get("actions", []))
            entry_signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": side,
                "entry": plan.get("entry_price"),
                "sl": plan.get("sl"),
                "tp": plan.get("tp"),
                "votes_long": vr_m15.get("votes_long"),
                "votes_short": vr_m15.get("votes_short"),
                "score_long": sl15,
                "score_short": ss15,
                "score_total": vr_m15.get("score_total"),
                "indicators": map_m15,
                "trend_h4": ind_h1.get("trend_h4"),
                "trend_d1": ind_d1.get("trend_d1") if ind_d1 else "-",  # <--- Truyền trend D1
                "created_at": time.time()
            }
            if entry_signal:
                entry_signal["quality_label"] = None
                entry_signal["quality_pct"] = None
                entry_signal["quality_threshold_met"] = None
            if config.get("engine", {}).get("promote_to_full", True):
                ok, msg = self.eng.promote_to_full(symbol, timeframe, plan, last_price)
                if ok:
                    actions.append(msg)
            self.cd.mark(symbol, timeframe, now_ts=now_ts, cooldown_sec=self.cooldown_min * 60)

        return {
            "entry_ready": entry_ready,
            "entry_signal": entry_signal,
            "actions": actions,
            "blocked_by": blocked_by,
            "side": side,
            "gates": {
                "h1_ok": h1_ok,
                "m15_ok": m15_ok,
                "anti_chase_ok": ac_ok
            },
            "stable": is_stable,
            "cooldown": in_cooldown,
        }

def init_facade(cfg: Dict) -> SharkEngineFacade:
    return SharkEngineFacade(cfg)
