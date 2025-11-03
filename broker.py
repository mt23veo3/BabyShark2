# -*- coding: utf-8 -*-
import time
import itertools
from typing import Dict, Any


class PaperBroker:
    def __init__(self, cfg: Dict):
        self.cfg = cfg or {}
        self._id = itertools.count(1)

    def now(self) -> float:
        return time.time()

    def place_limit(self, symbol: str, side: str, price: float, size: float, ttl_sec: int = 30) -> Dict[str, Any]:
        oid = f"paper_{next(self._id)}"
        now = self.now()
        return {
            "id": oid,
            "symbol": symbol,
            "side": side,
            "type": "limit",
            "price": float(price),
            "size": float(size),
            "status": "open",
            "created_at": float(now),
            "expires_at": float(now + max(1, int(ttl_sec))),
        }


def get_broker(cfg: Dict) -> PaperBroker:
    # Có thể mở rộng: nếu cfg.trading.mode == "live" -> trả CCXT broker
    return PaperBroker(cfg)
