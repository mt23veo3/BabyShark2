# mode_detector.py
from __future__ import annotations
from typing import Dict, Any

def _flt(x, default: float = 0.0) -> float:
    try: return float(x)
    except Exception: return float(default)

def detect_mode(indicators: Dict[str, Dict[str, Any]], ctx: Dict[str, Any]) -> str:
    """
    Trả về "SCALPER" hoặc "SWING".
    Tiêu chí:
      - SWING khi: ADX(H1) > 30 và ADX(H4) > 25 (nếu có) và VFI mạnh (ctx.vfi_score>~60) hoặc TREND_ALIGN
      - SCALPER trong các trường hợp còn lại (nén/sideway)
    Thiếu dữ liệu -> fallback an toàn = SCALPER.
    """
    adx_h1 = _flt(ctx.get("adx_h1"), 0.0)
    adx_h4 = _flt(ctx.get("adx_h4"), 0.0)
    macro  = str(ctx.get("macro_regime", "")).upper()
    vfi_score = _flt(ctx.get("vfi_score"), 0.0)  # nếu sau có tính composite

    # BBW(H1) có thể dùng nhận biết nén -> scalper
    bbw_h1 = 0.0
    try:
        h1 = indicators.get("H1") or {}
        bbw_h1 = _flt(h1.get("bbw_norm"), 0.0)
    except Exception:
        pass

    # Điều kiện swing
    swing_by_trend = (adx_h1 > 30.0 and (adx_h4 > 25.0 or macro == "TREND_ALIGN"))
    swing_by_vfi   = (vfi_score >= 60.0)
    if swing_by_trend and (swing_by_vfi or macro == "TREND_ALIGN"):
        return "SWING"

    # Nếu thị trường nén rõ rệt -> scalper
    if bbw_h1 > 0.0 and bbw_h1 < 0.02 and adx_h4 < 20.0:
        return "SCALPER"

    # Mặc định
    return "SCALPER"
