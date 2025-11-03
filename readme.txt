# BabyShark Signal Bot

## Mục đích
Bot đề xuất tín hiệu giao dịch tự động dựa trên snapshot dữ liệu thị trường.

## Cài đặt môi trường

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Chuẩn bị dữ liệu đầu vào

- Dữ liệu mẫu lưu tại: `data/snapshots.csv`
- Cấu trúc file CSV:
  ```
  close,direction,score_total,quality_pct,fast_points,slow_points,bars_since_breakout,prev_m15_high
  100,LONG,20,95,10,5,1,100
  101,LONG,20,95,10,5,2,100
  ...
  ```

## Chạy pipeline đề xuất tín hiệu

- File script: `run_signal_bot.py`
- Đầu ra: In kết quả đề xuất trên từng snapshot

```bash
python run_signal_bot.py
```

## Chạy backtest

- File script: `backtest_signal_bot.py`
- Đầu vào: `data/snapshots.csv`
- Đầu ra: Thống kê số lượng từng loại tín hiệu, ghi log ra file `backtest_results.log`

```bash
python backtest_signal_bot.py
```

## Ý nghĩa các loại tín hiệu

- `ENTRY`: Bot đề xuất vào lệnh
- `ENTRY_EARLY`: Đề xuất vào lệnh sớm (có thể cần xác nhận lại)
- `EXIT`: Bot đề xuất thoát lệnh
- `NO_SIGNAL`: Không có tín hiệu
- `FILTERED_OUT`: Snapshot bị loại bỏ do không đạt tiêu chí

## Mở rộng/tham khảo

- Có thể tích hợp thêm API, alert notification (Telegram, Discord...)
- Có thể điều chỉnh điều kiện filter, logic entry/exit để tối ưu hiệu quả.

---

**Liên hệ & đóng góp**  
Nếu bạn có ý tưởng mở rộng, vui lòng liên hệ hoặc tạo issue trên repo!
