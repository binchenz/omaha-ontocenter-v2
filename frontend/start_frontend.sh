#!/bin/bash
# 启动前端服务

echo "Installing dependencies (if needed)..."
if [ ! -d "node_modules" ]; then
    npm install
fi

echo "Starting frontend dev server..."
npm run dev
