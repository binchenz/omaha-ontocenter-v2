#!/bin/bash
# Omaha OntoCenter 云服务器部署脚本
# 使用方法: bash setup_server.sh

set -e

echo "=== Omaha OntoCenter 服务器部署 ==="
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 root 用户运行此脚本"
    exit 1
fi

# 1. 更新系统
echo "步骤 1/8: 更新系统..."
apt update && apt upgrade -y

# 2. 安装基础软件
echo "步骤 2/8: 安装基础软件..."
apt install -y python3.10 python3.10-venv python3-pip postgresql nginx git certbot python3-certbot-nginx

# 3. 配置 PostgreSQL
echo "步骤 3/8: 配置 PostgreSQL..."
read -p "请输入数据库密码: " DB_PASSWORD

sudo -u postgres psql << EOF
CREATE DATABASE omaha_cloud;
CREATE USER omaha WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE omaha_cloud TO omaha;
\q
EOF

echo "PostgreSQL 配置完成"

# 4. 克隆代码
echo "步骤 4/8: 克隆代码..."
read -p "请输入 Git 仓库地址: " GIT_REPO

mkdir -p /opt/omaha-cloud
cd /opt/omaha-cloud
git clone $GIT_REPO .

# 5. 配置 Python 环境
echo "步骤 5/8: 配置 Python 环境..."
python3.10 -m venv venv
source venv/bin/activate
cd backend
pip install -r requirements.txt

# 6. 配置环境变量
echo "步骤 6/8: 配置环境变量..."
read -p "请输入 Tushare Token: " TUSHARE_TOKEN
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

cat > /opt/omaha-cloud/backend/.env << EOF
DATABASE_URL=postgresql://omaha:$DB_PASSWORD@localhost/omaha_cloud
SECRET_KEY=$SECRET_KEY
TUSHARE_TOKEN=$TUSHARE_TOKEN
ACCESS_TOKEN_EXPIRE_MINUTES=43200
EOF

echo "环境变量配置完成"

# 7. 初始化数据库
echo "步骤 7/8: 初始化数据库..."
cd /opt/omaha-cloud/backend
source ../venv/bin/activate
alembic upgrade head

# 生成初始邀请码
python scripts/generate_invite_codes.py --count 10 > /root/invite_codes.txt
echo "邀请码已保存到 /root/invite_codes.txt"

# 8. 配置 systemd 服务
echo "步骤 8/8: 配置 systemd 服务..."
cp /opt/omaha-cloud/deployment/omaha-cloud.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable omaha-cloud
systemctl start omaha-cloud

echo ""
echo "=== 部署完成 ==="
echo "应用已启动在 http://localhost:8000"
echo "邀请码保存在 /root/invite_codes.txt"
echo ""
echo "下一步: 配置 Nginx 和 SSL"
echo "运行: bash /opt/omaha-cloud/deployment/setup_nginx.sh"
