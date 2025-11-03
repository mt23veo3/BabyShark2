import datetime
from services.constants import LOG_FILE

def log_access(path, user_agent, ip):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now()} - {ip} - {path} - {user_agent}\n")
    except Exception:
        pass

def log_error(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"ERROR {datetime.datetime.now()} - {msg}\n")
    except Exception:
        pass