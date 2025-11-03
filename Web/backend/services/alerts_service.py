import json
from services.constants import ALERTS_LOG

def safe_load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def safe_write_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_all_alerts(page=1, page_size=50):
    alerts = safe_load_json(ALERTS_LOG)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": len(alerts),
        "page": page,
        "page_size": page_size,
        "alerts": alerts[start:end]
    }

def get_unread_alerts():
    alerts = safe_load_json(ALERTS_LOG)
    return [a for a in alerts if not a.get("read", False)]

def mark_alert_as_read(alert_id):
    alerts = safe_load_json(ALERTS_LOG)
    updated = False
    for a in alerts:
        if str(a.get("id", "")) == str(alert_id):
            a["read"] = True
            updated = True
    if updated:
        safe_write_json(ALERTS_LOG, alerts)
        return {"success": True}
    else:
        return {"success": False, "msg": "Alert not found"}