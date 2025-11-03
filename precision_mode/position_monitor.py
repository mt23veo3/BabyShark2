from precision_mode.config import POSITION_CONFIG

class PositionMonitor:
    def __init__(self):
        self.active_positions = []
        self.risk_used = 0.0

    def open_position(self, symbol: str, size: float, entry_price: float, risk: float):
        self.active_positions.append({
            "symbol": symbol,
            "size": size,
            "entry_price": entry_price,
            "risk": risk
        })
        self.risk_used += risk

    def close_position(self, symbol: str):
        for p in self.active_positions:
            if p["symbol"] == symbol:
                self.risk_used -= p["risk"]
                self.active_positions.remove(p)
                break

    def can_open_new(self, risk: float) -> bool:
        # Giới hạn tổng risk theo config
        return (self.risk_used + risk) <= POSITION_CONFIG["max_total_risk"]

    def position_count(self) -> int:
        return len(self.active_positions)

    def sync(self, positions: list):
        # Đồng bộ trạng thái từ nguồn bên ngoài (ví dụ: sàn, database)
        self.active_positions = positions
        self.risk_used = sum(p["risk"] for p in positions)
