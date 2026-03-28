#!/bin/bash
# 部署性能监控更新到云服务器

set -e

SERVER="root@69.5.23.70"
REMOTE_PATH="/opt/omaha-cloud"
PASSWORD="zbc67326013"

echo "=========================================="
echo "部署性能监控更新"
echo "=========================================="

# 1. 打包backend目录
echo "1. 打包backend代码..."
tar -czf backend_perf_update.tar.gz \
    backend/app/api/public_query.py \
    backend/app/schemas/public_query.py \
    backend/app/services/cache_service.py

# 2. 上传到服务器
echo "2. 上传到服务器..."
sshpass -p "${PASSWORD}" scp backend_perf_update.tar.gz ${SERVER}:${REMOTE_PATH}/

# 3. 在服务器上解压并重启服务
echo "3. 解压并重启服务..."
sshpass -p "${PASSWORD}" ssh ${SERVER} << 'ENDSSH'
cd /opt/omaha-cloud
tar -xzf backend_perf_update.tar.gz
rm backend_perf_update.tar.gz

# 重启backend服务
cd backend
source /opt/omaha-cloud/venv/bin/activate
pkill -f "uvicorn app.main:app" || true
sleep 2
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
sleep 3

# 检查服务状态
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "✓ Backend服务重启成功"
else
    echo "✗ Backend服务重启失败"
    exit 1
fi
ENDSSH

# 4. 清理本地临时文件
echo "4. 清理临时文件..."
rm backend_perf_update.tar.gz

echo ""
echo "=========================================="
echo "✓ 部署完成"
echo "=========================================="
echo ""
echo "验证命令:"
echo "curl -s http://69.5.23.70/api/public/v1/query \\"
echo "  -H 'Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"object_type\":\"Stock\",\"filters\":{\"industry\":\"银行\"},\"limit\":1}' | python -m json.tool"
