import pandas as pd
from datetime import datetime, timedelta

df = pd.read_csv('entries_reasons.csv')
df['dt'] = pd.to_datetime(df['timestamp'], unit='s')
df['weekday'] = df['dt'].dt.weekday  # 0=Monday, ..., 6=Sunday

# Tìm ngày chủ nhật gần nhất
latest_sunday = df[df['weekday'] == 6]['dt'].dt.date.max()

# Giữ lại dữ liệu của chủ nhật gần nhất
df_keep = df[(df['weekday'] == 6) & (df['dt'].dt.date == latest_sunday)].copy()

df_keep = df_keep.drop(columns=['dt', 'weekday'], errors='ignore')
df_keep.to_csv('entries_reasons.csv', index=False)

print(f"Đã xóa dữ liệu, chỉ giữ lại chủ nhật gần nhất: {latest_sunday}")
