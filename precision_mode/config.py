# Cấu hình và feature flag cho precision_mode

# Feature flag: Bật/tắt chế độ precision
PRECISION_MODE_ENABLED = True

# Ngưỡng điểm nền cho từng khung và chất lượng
THRESHOLDS = {
    "M15": 14,
    "H1": 14,
    "M5": 15,
    "quality": 88,
}

# Điều kiện gates nền (điểm nhanh/chậm, range)
GATES = {
    "fast_min": 9,
    "slow_min": 3,
    "range_downweight_when_adx_strong": True,
}

# Cửa sổ xác nhận sớm (Early Trigger)
EARLY_TRIGGER = {
    "early_trigger_max_bars": 3,      # Số bar tối đa kể từ breakout để được xem là kích hoạt sớm
    "bonus_score": 5,                 # Điểm cộng khi nằm trong early window
    "quality_threshold": 90,          # Ngưỡng chất lượng để cộng điểm
    "quality_bonus": 2,               # Điểm cộng nếu vượt ngưỡng chất lượng
}

# Các bộ lọc muộn (Late Filter)
LATE_FILTER = {
    "max_bars_since_breakout": 1,
    "max_dist_vwap_pct": 0.6,
    "max_dist_ema20_pct": 0.8,
    "block_volume_climax": True,
    "max_zscore_bandwidth": 1.0,
}

# Cấu hình vùng vào lệnh (Entry Planner)
ENTRY_CONFIG = {
    "breakout_zone_offsets": [00, 2.0],  # offset cho LONG: [prev_M15_high−0.15%, +0.05%]
    "pullback_offset_pct": 0.1,              # ±0.1% quanh EMA20/VWAP
    "buy_through": {"dist_vwap_max": 0.4, "size": 0.5},
    "retest_timeout_bars": 2,                # auto-cancel sau 2 nến M15
}

# Quản trị rủi ro (Risk)
RISK_CONFIG = {
    "sl_atr_multiple": 1.0,
    "rr_min": 1.5,
    "rr_target": 1.8,
}

# Các key cooldown/scheduler nếu cần thêm
COOLDOWN_CONFIG = {
    "m15": 0,  # phút cooldown trên M15
    "m5": 0,   # phút cooldown trên M5
}

# ---- Chú thích: ----
# Bạn có thể sửa giá trị trực tiếp trong file này để thay đổi hành vi module
# Nếu PRECISION_MODE_ENABLED = False, module này không ảnh hưởng hệ thống hiện tại
EXIT_CONFIG = {
    "tp_pct": 2,                # Take profit 2%
    "trailing_stop_pct": 1,     # Trailing stop 1%
    "min_score": 10,            # Thoát nếu score <= 10
}

POSITION_CONFIG = {
    "max_total_risk": 2.0,   # Tổng risk cho phép (theo đơn vị hệ thống, ví dụ %NAV)
    "max_positions": 5,      # Số lượng vị thế tối đa
}

ORDER_CONFIG = {
    "max_orders": 10,           # Số lượng lệnh tối đa cho phép
    "max_order_size": 1.0,      # Kích thước lệnh tối đa
}
