from __future__ import annotations
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Mapping, List
from urllib import request, error

# ============== CẤU HÌNH ==============
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None  # type: ignore

LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh") if ZoneInfo else None

# Cho phép style "classic" (mặc định) hoặc "compact" (chưa dùng)
EMBED_STYLE = os.getenv("DISCORD_EMBED_STYLE", "classic").strip().lower()

# Cho phép biểu tượng tiêu đề (none / check / custom:...)
EMBED_TITLE_ICON = os.getenv("DISCORD_EMBED_TITLE_ICON", "none").strip().lower()

FALLBACK_SCORE_TOTAL = 18.0
try:
    FALLBACK_SCORE_TOTAL = float(os.getenv("DISCORD_FALLBACK_SCORE_TOTAL", "18"))
except Exception:
    pass

# Ngưỡng chất lượng
Q_STRONG = float(os.getenv("DISCORD_QUALITY_STRONG_PCT", "85"))
Q_GOOD   = float(os.getenv("DISCORD_QUALITY_GOOD_PCT", "70"))
Q_MIN    = float(os.getenv("DISCORD_QUALITY_MIN_PCT", "75"))

# Emoji
EMO_VOTE_UP = "🟢"
EMO_VOTE_DOWN = "🔴"
EMO_TP = "🏆"
EMO_SL = "⛔"
EMO_ENTRY = "⚔️"
EMO_LONG = "🟢"
EMO_SHORT = "🔴"
EMO_NEU = "⚪"
EMO_CHECK = "✅"

# Danh sách hiển thị chỉ báo (giống bản bạn muốn giữ nguyên giao diện)
INDICATORS_LEFT: List[str] = [
    "ADX", "BollingerBands", "Chaikin_MF", "EMA200", "MA50", "MACD"
]
INDICATORS_RIGHT: List[str] = [
    "Range", "RSI", "StochRSI", "Supertrend", "Volume_Spike", "VWAP"
]

DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Accept-Language": "vi-VN,vi;q=0.9",
    "User-Agent": "BabySharkBot/1.0 (+https://github.com/mt23veo3/DIY)",
    "Referer": "https://discord.com/",
}

DECIMALS_BY_SYMBOL: Dict[str, int] = {}


# ============== TIỆN ÍCH ==============

def _guess_decimals(symbol: str, price: float) -> int:
    if symbol in DECIMALS_BY_SYMBOL:
        return DECIMALS_BY_SYMBOL[symbol]
    if symbol.endswith("USDT"):
        if price >= 100000: return 0
        if price >= 10000:  return 1
        if price >= 1000:   return 2
        if price >= 100:    return 3
        if price >= 10:     return 4
        return 5
    return 4

def _fmt_price(symbol: str, price: Optional[float]) -> str:
    if price is None or (isinstance(price, float) and (math.isnan(price) or math.isinf(price))):
        return "-"
    try:
        p = float(price)
    except Exception:
        return str(price)
    decimals = _guess_decimals(symbol, p)
    return f"{p:,.{decimals}f}"

fmt_price = _fmt_price

def _fmt_votes(v_long: Optional[int], v_short: Optional[int]) -> str:
    v_long = int(v_long or 0)
    v_short = int(v_short or 0)
    return f"{EMO_LONG} {v_long} / {EMO_SHORT} {v_short}"

def _ensure_tz(dt: Any) -> datetime:
    if dt is None:
        now = datetime.now(timezone.utc)
        return now.astimezone(LOCAL_TZ) if LOCAL_TZ else now
    if isinstance(dt, (float, int)):
        aware = datetime.fromtimestamp(dt, tz=timezone.utc)
        return aware.astimezone(LOCAL_TZ) if LOCAL_TZ else aware
    if isinstance(dt, str):
        # Thử parse epoch string trước
        try:
            ts = float(dt)
            aware = datetime.fromtimestamp(ts, tz=timezone.utc)
            return aware.astimezone(LOCAL_TZ) if LOCAL_TZ else aware
        except Exception:
            pass
        try:
            aware = datetime.fromisoformat(dt)
            if aware.tzinfo is None:
                aware = aware.replace(tzinfo=timezone.utc)
            return aware.astimezone(LOCAL_TZ) if LOCAL_TZ else aware
        except Exception:
            now = datetime.now(timezone.utc)
            return now.astimezone(LOCAL_TZ) if LOCAL_TZ else now
    if hasattr(dt, "tzinfo"):
        if dt.tzinfo is None:
            aware = dt.replace(tzinfo=timezone.utc)
            return aware.astimezone(LOCAL_TZ) if LOCAL_TZ else aware
        return dt.astimezone(LOCAL_TZ) if LOCAL_TZ else dt
    now = datetime.now(timezone.utc)
    return now.astimezone(LOCAL_TZ) if LOCAL_TZ else now

def _ind_emoji(val: str) -> str:
    v = (val or "").upper()
    if v == "LONG": return EMO_LONG
    if v == "SHORT": return EMO_SHORT
    return EMO_NEU

def _resolve_score_total(sig: Dict[str, Any]) -> Optional[float]:
    # Hỗ trợ nhiều tên khóa khác nhau
    candidates = [
        "score_total", "score_max", "total_score", "scores_total",
        "indicators_total_weight", "total_weight"
    ]
    for k in candidates:
        if k in sig and sig[k] is not None:
            try:
                return float(sig[k])
            except Exception:
                pass
    meta = sig.get("meta") or {}
    if isinstance(meta, Mapping):
        for k in candidates:
            if k in meta and meta[k] is not None:
                try:
                    return float(meta[k])
                except Exception:
                    pass
    breakdown = sig.get("breakdown")
    # fallback
    return FALLBACK_SCORE_TOTAL

def _derive_quality(score_long: Optional[float], score_short: Optional[float], score_total: Optional[float]) -> Optional[Dict[str, Any]]:
    try:
        if score_long is None or score_short is None or score_total is None or score_total <= 0:
            return None
        pct = max(score_long, score_short) / score_total * 100.0
        if pct >= Q_STRONG:
            label = "MẠNH"
        elif pct >= Q_GOOD:
            label = "TỐT"
        else:
            label = "TRUNG BÌNH"
        return {
            "quality_pct": pct,
            "quality_label": label,
            "quality_threshold_met": pct >= Q_MIN
        }
    except Exception:
        return None

def _title_with_icon(text: str) -> str:
    if EMBED_TITLE_ICON == "none":
        return text
    if EMBED_TITLE_ICON.startswith("custom:"):
        icon = EMBED_TITLE_ICON.split("custom:", 1)[1].strip()
        return f"{icon} {text}".strip()
    if EMBED_TITLE_ICON == "check":
        return f"☑️ {text}"
    return text

# ============== BUILD CLASSIC EMBED (GIỮ NGUYÊN PHONG CÁCH CŨ) ==============

def _build_classic_embed(sig: Dict[str, Any]) -> Dict[str, Any]:
    symbol = sig.get("symbol", "?")
    timeframe = sig.get("timeframe", "")
    side = str(sig.get("signal", "")).upper()
    entry = sig.get("entry")
    tp = sig.get("tp")
    sl = sig.get("sl")
    votes_long = sig.get("votes_long")
    votes_short = sig.get("votes_short")
    indicators: Dict[str, str] = sig.get("indicators") or {}
    score_long = sig.get("score_long")
    score_short = sig.get("score_short")
    score_total = _resolve_score_total(sig)
    trend_h4 = sig.get("trend_h4")
    trend_d1 = sig.get("trend_d1")
    created_at = _ensure_tz(sig.get("created_at"))

    quality_label = sig.get("quality_label")
    quality_pct = sig.get("quality_pct")
    quality_threshold_met = sig.get("quality_threshold_met")

    # Derive quality nếu chưa có
    if quality_label is None or quality_pct is None:
        q = _derive_quality(score_long, score_short, score_total)
        if q:
            quality_label = q["quality_label"]
            quality_pct = q["quality_pct"]
            quality_threshold_met = q["quality_threshold_met"]

    entry_txt = f"{EMO_ENTRY} {fmt_price(symbol, entry)}"
    tp_txt = f"{EMO_TP} {fmt_price(symbol, tp)}"
    sl_txt = f"{EMO_SL} {fmt_price(symbol, sl)}"
    votes_str = _fmt_votes(votes_long, votes_short)

    def render_list(keys: List[str]) -> str:
        lines = []
        for k in keys:
            v = indicators.get(k, "-")
            lines.append(f"{_ind_emoji(v)} {k}: {str(v).upper() if v else '-'}")
        return "\n".join(lines) if lines else "-"

    left_block = render_list(INDICATORS_LEFT)
    right_block = render_list(INDICATORS_RIGHT)

    score_line = None
    if score_long is not None and score_short is not None and score_total is not None:
        score_line = f"{score_long} / {score_short} (tổng {score_total})"
    elif score_long is not None and score_short is not None:
        score_line = f"{score_long} / {score_short}"

    quality_line = None
    if quality_label is not None and quality_pct is not None:
        base = f"{quality_label.upper()} ({int(round(float(quality_pct)))}%)"
        if bool(quality_threshold_met):
            base += " (>= ngưỡng)"
        quality_line = base

    title = _title_with_icon("TÍN HIỆU MỚI")
    color = 0x00C853 if side == "LONG" else 0xD50000

    fields = [
        {"name": "Cặp", "value": symbol, "inline": True},
        {"name": "Khung thời gian", "value": timeframe, "inline": True},
        {"name": "Chiều giao dịch", "value": side, "inline": True},

        {"name": "Giá vào lệnh", "value": entry_txt, "inline": True},
        {"name": "Dừng lỗ", "value": sl_txt, "inline": True},
        {"name": "Chốt lời", "value": tp_txt, "inline": True},

        {"name": "Chỉ báo (1/2)", "value": left_block or "-", "inline": True},
        {"name": "Chỉ báo (2/2)", "value": right_block or "-", "inline": True},
        {"name": "Bình chọn", "value": votes_str, "inline": True},
    ]

    if score_line:
        fields.append({"name": "Điểm L/S", "value": score_line, "inline": True})
    # Xu hướng luôn có
    fields.append({"name": "Xu hướng", "value": f"H4: {trend_h4 or '-'} | D1: {trend_d1 or '-'}", "inline": True})
    if quality_line:
        fields.append({"name": "Chất lượng", "value": quality_line, "inline": False})

    embed: Dict[str, Any] = {
        "title": title,
        "color": color,
        "fields": fields,
        "timestamp": created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "footer": {
            "text": "Tín hiệu tự động • " + created_at.strftime("%d/%m/%Y %H:%M")
        },
    }
    return embed


# ============== ACTION EMBED (PHỤ - NẾU MUỐN GIỮ) ==============

def _build_action_embed(act: Dict[str, Any]) -> Dict[str, Any]:
    symbol = act.get("symbol", "?")
    timeframe = act.get("timeframe") or act.get("tf") or ""
    side = str(act.get("side") or act.get("direction") or "").upper()
    action_name = str(act.get("action") or act.get("event") or "").upper()
    price = act.get("price")
    size = act.get("size")
    order_id = act.get("id") or act.get("order_id")
    note = act.get("note") or ""
    created_at = _ensure_tz(act.get("created_at"))

    if "CANCEL" in action_name:
        ttl_title = "HỦY LỆNH"
    elif "FILL" in action_name:
        ttl_title = "KHỚP LỆNH"
    elif "PLACE" in action_name:
        ttl_title = "ĐẶT LỆNH"
    else:
        ttl_title = "HÀNH ĐỘNG"

    color = 0x00C853 if side == "LONG" else (0xD50000 if side == "SHORT" else 0x607D8B)
    fields = []
    if note:
        fields.append({"name": "Ghi chú", "value": note[:1000], "inline": False})

    embed: Dict[str, Any] = {
        "title": f"{symbol} {timeframe} | {ttl_title}",
        "color": color,
        "fields": [
            {"name": "Chiều", "value": side or "-", "inline": True},
            {"name": "Giá", "value": fmt_price(symbol, price), "inline": True},
            {"name": "Khối lượng", "value": str(size) if size is not None else "-", "inline": True},
        ] + fields,
        "timestamp": created_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "footer": {"text": "Hành động tự động • " + created_at.strftime("%d/%m/%Y %H:%M")},
    }
    if order_id:
        embed["fields"].append({"name": "ID", "value": order_id, "inline": True})
    return embed


# ============== PUBLIC BUILDERS ==============

def build_signal_embed(sig: Dict[str, Any], preview: bool = False) -> Dict[str, Any]:
    # Classic style duy nhất
    embed = _build_classic_embed(sig)
    if preview:
        embed["title"] = f"[XEM TRƯỚC] {embed.get('title', '')}"
    return embed

def build_action_embed(act: Dict[str, Any]) -> Dict[str, Any]:
    return _build_action_embed(act)


# ============== SENDERS ==============

def _extract_webhook_from_obj(obj: Any) -> Optional[str]:
    candidate_keys = [
        "webhook_url",
        "discord_webhook_url",
        "discord_webhook",
        "main_webhook",
        "DISCORD_WEBHOOK_URL",
        "DISCORD_MAIN_WEBHOOK",
        "webhook",
        "url",
    ]
    if isinstance(obj, Mapping):
        for k in candidate_keys:
            if k in obj and obj[k]:
                return str(obj[k])
        return None
    for k in candidate_keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if v:
                return str(v)
    if isinstance(obj, str):
        return obj
    return None

def _resolve_webhook(env_keys: List[str], fallback: Any) -> Optional[str]:
    url = _extract_webhook_from_obj(fallback)
    if url:
        return url
    for k in env_keys:
        v = os.getenv(k)
        if v:
            return v
    return None

def _post_webhook(webhook_url: str, payload: Dict[str, Any], max_retries: int = 1) -> int:
    if not isinstance(webhook_url, str) or not webhook_url.startswith("http"):
        short = str(webhook_url)
        if len(short) > 60: short = short[:60] + "..."
        print(f"[WARN] Địa chỉ webhook Discord không hợp lệ: {short}", file=sys.stderr)
        return -1

    data = json.dumps(payload).encode("utf-8")
    last_status = -1
    for attempt in range(max_retries + 1):
        req = request.Request(
            webhook_url,
            data=data,
            headers=DEFAULT_HEADERS,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=15) as resp:
                return int(resp.getcode())  # 204 if success
        except error.HTTPError as e:
            last_status = int(e.code)
            body = ""
            try:
                body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                pass
            if e.code == 429:
                retry_after = 1.0
                try:
                    j = json.loads(body or "{}")
                    retry_after = float(j.get("retry_after", retry_after))
                except Exception:
                    pass
                sleep_s = min(max(retry_after + 0.1, 0.5), 10.0)
                print(f"[WARN] Discord 429 rate limit. Đợi {sleep_s:.2f}s", file=sys.stderr)
                time.sleep(sleep_s)
                continue
            if e.code == 403:
                print(f"[WARN] Discord 403 (có thể Cloudflare WAF).", file=sys.stderr)
            print(f"[WARN] Discord HTTPError {e.code}: {body}", file=sys.stderr)
            return last_status
        except Exception as ex:
            last_status = -1
            print(f"[WARN] Gửi Discord thất bại: {ex}", file=sys.stderr)
            return last_status
    return last_status

def send_text(webhook_url: Any, text: str) -> bool:
    url = _resolve_webhook(
        ["DISCORD_WEBHOOK_URL", "DISCORD_MAIN_WEBHOOK", "WEBHOOK_URL"],
        webhook_url,
    )
    if not url:
        print("[WARN] Thiếu webhook Discord", file=sys.stderr)
        return False
    status = _post_webhook(url, {"content": text})
    ok = status in (200, 204)
    if not ok:
        print(f"[WARN] Gửi text Discord lỗi, status={status}", file=sys.stderr)
    return ok

def send_signal(webhook_url: Any, sig: Dict[str, Any]) -> bool:
    url = _resolve_webhook(
        ["DISCORD_WEBHOOK_URL", "DISCORD_MAIN_WEBHOOK", "WEBHOOK_URL"],
        webhook_url,
    )
    if not url:
        print("[WARN] Thiếu webhook Discord", file=sys.stderr)
        return False
    embed = build_signal_embed(sig, preview=False)
    payload = {"embeds": [embed]}
    status = _post_webhook(url, payload)
    ok = status in (200, 204)
    if not ok:
        print(f"[WARN] Gửi tín hiệu Discord lỗi, status={status}", file=sys.stderr)
    return ok

def send_action(webhook_url: Any, act: Dict[str, Any]) -> bool:
    # Dùng embed hành động riêng (nếu muốn hiển thị lifecycle)
    url = _resolve_webhook(
        ["DISCORD_WEBHOOK_URL", "DISCORD_MAIN_WEBHOOK", "WEBHOOK_URL"],
        webhook_url,
    )
    if not url:
        print("[WARN] Thiếu webhook Discord", file=sys.stderr)
        return False
    embed = build_action_embed(act)
    payload = {"embeds": [embed]}
    status = _post_webhook(url, payload)
    ok = status in (200, 204)
    if not ok:
        print(f"[WARN] Gửi action Discord lỗi, status={status}", file=sys.stderr)
    return ok

# Async wrappers (nếu cần)
async def send_discord_signal(sig: Dict[str, Any], webhook_url: Any = None) -> bool:
    return send_signal(webhook_url, sig)

async def send_discord_action(act: Dict[str, Any], webhook_url: Any = None) -> bool:
    return send_action(webhook_url, act)

__all__ = [
    "fmt_price",
    "build_signal_embed",
    "build_action_embed",
    "send_text",
    "send_signal",
    "send_action",
    "send_discord_signal",
    "send_discord_action",
]
