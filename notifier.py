from __future__ import annotations
import json, os, time
from typing import Any, Iterable
from urllib import request as _urlreq, error as _urlerr

DISCORD_LIMIT = 2000  # characters

def _chunks(s: str, n: int) -> Iterable[str]:
    for i in range(0, len(s), n):
        yield s[i:i+n]

def _normalize_webhook(url: str) -> str:
    if not url:
        return ""
    u = url.strip()
    # Tự chuyển domain cũ -> mới
    u = u.replace("://discordapp.com", "://discord.com")
    # Cắt query lạ; giữ ?wait=true nếu có
    if "/api/webhooks/" in u:
        parts = u.split("?")
        base = parts[0]
        q = "?wait=true" if (len(parts) > 1 and "wait=true" in parts[1]) else ""
        return base + q
    return u

class Notifier:
    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or {}
        ncfg = (self.cfg.get("notifier") or {})
        self.webhook = _normalize_webhook(os.getenv("DISCORD_WEBHOOK") or ncfg.get("discord_webhook") or "")
        self.enabled = bool(ncfg.get("enabled", True))
        self.username = ncfg.get("username", "BabyShark")
        self.notify_decision = bool(ncfg.get("notify_decision", True))

    def _http_post(self, url: str, payload: dict) -> int:
        data = json.dumps(payload).encode("utf-8")
        req = _urlreq.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                # Thêm UA chuẩn để tránh 403 do chặn client lạ
                "User-Agent": "BabySharkBot/1.0 (+https://discord.com/webhook) Python-urllib",
            },
            method="POST",
        )
        try:
            with _urlreq.urlopen(req, timeout=6) as resp:
                return getattr(resp, "status", 204)
        except _urlerr.HTTPError as e:
            print(f"[NOTIFIER] HTTP {e.code} sending to Discord", flush=True)
            return int(e.code)
        except Exception as e:
            print(f"[NOTIFIER] send error: {e}", flush=True)
            return -1

    def _post(self, content: str, username: str | None = None):
        if not self.enabled:
            print("[NOTIFIER] disabled", flush=True); return
        if not self.webhook:
            print("[NOTIFIER] missing webhook; set notifier.discord_webhook or ENV DISCORD_WEBHOOK", flush=True); return

        payload = {"username": username or self.username, "content": content}

        # Try 1
        code = self._http_post(self.webhook, payload)

        # Nếu 403 hoặc 404, thử sửa domain một lần nữa và thêm ?wait=true rồi retry
        if code in (403, 404):
            retry_url = _normalize_webhook(self.webhook)
            if "wait=" not in retry_url:
                retry_url = retry_url + ("?wait=true" if "?" not in retry_url else "&wait=true")
            if retry_url != self.webhook:
                print(f"[NOTIFIER] retrying with normalized URL: {retry_url}", flush=True)
                self.webhook = retry_url
                code2 = self._http_post(self.webhook, payload)
                code = code2

        if code not in (-1, 200, 201, 202, 204):
            print(f"[NOTIFIER] Discord responded with HTTP {code}. "
                  f"Check webhook URL/permissions or regenerate the webhook.", flush=True)

    def _send(self, content: str, username: str | None = None):
        if not content: return
        for part in _chunks(content, DISCORD_LIMIT - 20):
            self._post(part, username=username)
            time.sleep(0.1)

    # ----------- Public helpers -----------
    def ping(self, msg: str = "BabyShark is alive"):
        self._send(f"🦈 {msg}")

    def decision(self, symbol: str, side: str, conf: float, flow: float):
        if not self.notify_decision: return
        self._send(f"📈 DECISION | {symbol} → **{side}** | conf={conf:.2f} | flow={flow:.2f}")

    def trade_open(self, symbol: str, side: str, qty: float, price: float):
        self._send(f"✅ OPEN | {symbol} {side} | qty={qty:.6f} | price={price:.4f}")

    def trade_reduce(self, symbol: str, side: str, qty: float, price: float, reason: str = ""):
        self._send(f"➖ REDUCE | {symbol} {side} | qty={qty:.6f} | price={price:.4f} | {reason}")

    def trade_close(self, symbol: str, side: str, qty: float, price: float, reason: str = ""):
        self._send(f"🧮 CLOSE | {symbol} {side} | qty={qty:.6f} | price={price:.4f} | {reason}")

    def vfi_exit(self, symbol: str, side: str, reason: str):
        self._send(f"⚠️ VFI EXIT | {symbol} {side} | {reason}")

    def error(self, msg: str):
        self._send(f"🚨 ERROR | {msg}")
