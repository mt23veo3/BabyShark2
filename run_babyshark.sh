#!/bin/bash

# Kích hoạt venv cho backend
cd /home/mt23veo3/BabyShark/Web/backend
source ../../.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Chạy frontend (React build với serve)
cd /home/mt23veo3/BabyShark/Web/frontend
serve -s build -l 3000 &

# Giữ script không kết thúc cho đến khi tất cả process con kết thúc
wait
