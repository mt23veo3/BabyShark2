import csv

# Đường dẫn file – sửa lại nếu cần
SIM_CSV = "trades_sim_log.csv"
OUT_CSV = "trades_log.csv"

# Cột chuẩn mà dashboard/backend web đang dùng
OUT_FIELDS = [
    "symbol", "timeframe", "side", "stage", "entry", "exit", "pnl", "pnl_r",
    "sl", "tp", "size", "opened_at", "closed_at", "status"
]

# Map cột input (trades_sim_log) -> output (trades_log)
MAP = {
    "symbol": "symbol",
    "timeframe": "stage",  # Nếu không có, để mặc định "sim" hoặc copy stage
    "side": "direction",
    "stage": "stage",
    "entry": "entry",
    "exit": "close_price",
    "pnl": "result",
    "pnl_r": "r_value",
    "sl": "sl",
    "tp": "tp",
    "size": "size",
    "opened_at": "time_open",
    "closed_at": "time_close",
    "status": "status",
}

def convert():
    with open(SIM_CSV, newline='', encoding='utf-8') as fin, \
         open(OUT_CSV, 'w', newline='', encoding='utf-8') as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=OUT_FIELDS)
        writer.writeheader()
        for row in reader:
            out_row = {}
            for out_col, in_col in MAP.items():
                value = row.get(in_col, "")
                # Nếu thiếu giá trị "timeframe", có thể để là "sim"
                if out_col == "timeframe" and not value:
                    value = "sim"
                out_row[out_col] = value
            writer.writerow(out_row)
    print(f"✅ Đã chuyển đổi {SIM_CSV} -> {OUT_CSV} cho dashboard web!")

if __name__ == "__main__":
    convert()