import json
import os

LAST_SIGNAL_FILE = "last_signal.json"

def load_last_signal():
    if not os.path.exists(LAST_SIGNAL_FILE):
        return {}
    with open(LAST_SIGNAL_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def save_last_signal(state):
    with open(LAST_SIGNAL_FILE, "w") as f:
        json.dump(state, f)
