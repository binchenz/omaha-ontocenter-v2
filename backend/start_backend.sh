#!/bin/bash
# 启动后端服务

echo "Starting backend server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
