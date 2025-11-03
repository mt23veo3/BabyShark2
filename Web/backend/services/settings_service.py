import json
from services.constants import TRADE_LOG, SIGNALS_LOG, TRADE_STATE, CONFIG, ALERTS_LOG

CONFIG_FILE = "../../config.json"

def safe_load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def safe_write_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_settings():
    return safe_load_json(CONFIG_FILE)

def get_setting_by_key(key):
    config = safe_load_json(CONFIG_FILE)
    return {key: config.get(key, None)}

def update_settings(payload):
    config = safe_load_json(CONFIG_FILE)
    config.update(payload)
    safe_write_json(CONFIG_FILE, config)
    return {"success": True, "updated": payload}