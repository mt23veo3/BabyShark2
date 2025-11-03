import csv
from services.constants import TRADE_LOG

def safe_float(val, default=0.0):
    try:
        if val in (None, "", "None"):
            return default
        return float(val)
    except Exception:
        return default

def safe_load_csv(path):
    result = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for k, v in row.items():
                    if v == "None":
                        row[k] = ""
                result.append(row)
    except Exception:
        pass
    return result

def get_all_orders(page=1, page_size=50):
    orders = safe_load_csv(TRADE_LOG)
    # Sắp xếp order mới nhất trên cùng theo opened_at giảm dần
    orders = sorted(orders, key=lambda o: safe_float(o.get("opened_at", 0)), reverse=True)
    start = (page - 1) * page_size
    end = start + page_size
    for o in orders:
        o["order_time"] = o.get("opened_at", "")
    return {
        "total": len(orders),
        "page": page,
        "page_size": page_size,
        "orders": orders[start:end]
    }

def get_open_orders():
    orders = safe_load_csv(TRADE_LOG)
    orders = [o for o in orders if o.get("status", "").lower() == "open"]
    orders = sorted(orders, key=lambda o: safe_float(o.get("opened_at", 0)), reverse=True)
    for o in orders:
        o["order_time"] = o.get("opened_at", "")
    return orders

def get_closed_orders():
    orders = safe_load_csv(TRADE_LOG)
    orders = [o for o in orders if o.get("status", "").lower() == "closed"]
    orders = sorted(orders, key=lambda o: safe_float(o.get("opened_at", 0)), reverse=True)
    for o in orders:
        o["order_time"] = o.get("opened_at", "")
    return orders

def get_order_by_id(order_id):
    orders = safe_load_csv(TRADE_LOG)
    for o in orders:
        if o.get("order_id", "") == order_id:
            o["order_time"] = o.get("opened_at", "")
            return o
    return {}