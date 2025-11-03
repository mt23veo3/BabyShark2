import os
import getpass
from services.constants import TRADE_LOG, SIGNALS_LOG, TRADE_STATE, CONFIG, ALERTS_LOG

def get_user_info():
    # Có thể mở rộng lấy từ DB hoặc auth real, demo trả về user hệ thống
    return {
        "user": getpass.getuser(),
        "uid": str(os.getuid()) if hasattr(os, "getuid") else "",
        "home": os.path.expanduser("~"),
    }

def get_session_info():
    # Có thể mở rộng lưu session thực, demo trả về dummy info
    return {
        "session": "active",
        "dashboard_version": "1.0.0",
        "env": os.environ.get("ENV", "dev"),
    }