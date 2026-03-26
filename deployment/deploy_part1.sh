#!/bin/bash
# 第1部分：系统更新和软件安装

set -e
echo "=== 开始部署 Omaha OntoCenter ==="

# 生成密码
DB_PASSWORD="omaha_$(openssl rand -hex 16)"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)
TUSHARE_TOKEN="044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90"

echo "步骤 1/10: 更新系统..."
apt update -qq

echo "步骤 2/10: 安装软件..."
apt install -y python3.10 python3.10-venv python3-pip postgresql postgresql-contrib nginx git curl

echo "步骤 3/10: 启动 PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql
sleep 3
