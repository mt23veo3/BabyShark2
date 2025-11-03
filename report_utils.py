# -*- coding: utf-8 -*-
def format_votes(indicators: dict, weights: dict) -> str:
    """
    Hiển thị đủ 10 chỉ báo theo thứ tự khóa trong weights của đúng timeframe.
    indicators: {name: "LONG"/"SHORT"/"NEUTRAL"}
    weights:    {name: float}
    """
    icon = {"LONG": "🟢", "SHORT": "🔴", "NEUTRAL": "⚪", "-": "⚪", None: "⚪"}
    lines = []
    for name, w in weights.items():
        sig = (indicators or {}).get(name, "NEUTRAL")
        lines.append(f"{icon.get(sig, '⚪')} {name} ({w}) → {sig}")
    return "\n".join(lines)
