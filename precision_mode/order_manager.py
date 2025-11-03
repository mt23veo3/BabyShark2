from precision_mode.config import ORDER_CONFIG

class OrderManager:
    def __init__(self):
        self.orders = []  # danh sách lệnh đã đặt

    def place_order(self, symbol: str, side: str, size: float, price: float):
        order = {
            "symbol": symbol,
            "side": side,  # "BUY" hoặc "SELL"
            "size": size,
            "price": price,
            "status": "OPEN"
        }
        self.orders.append(order)
        return order

    def fill_order(self, symbol: str, side: str):
        for order in self.orders:
            if order["symbol"] == symbol and order["side"] == side and order["status"] == "OPEN":
                order["status"] = "FILLED"
                return order
        return None

    def cancel_order(self, symbol: str, side: str):
        for order in self.orders:
            if order["symbol"] == symbol and order["side"] == side and order["status"] == "OPEN":
                order["status"] = "CANCELLED"
                return order
        return None

    def active_orders(self):
        return [o for o in self.orders if o["status"] == "OPEN"]

    def sync_orders(self, orders: list):
        # đồng bộ trạng thái lệnh từ nguồn bên ngoài
        self.orders = orders
