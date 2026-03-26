#!/bin/bash
# 定制部署脚本 - 火山引擎服务器 69.5.23.70
# 使用方法:
# 1. 上传整个项目到服务器: scp -r omaha_ontocenter root@69.5.23.70:/tmp/
# 2. SSH 登录: ssh root@69.5.23.70
# 3. 运行此脚本: bash /tmp/omaha_ontocenter/deployment/deploy_to_69.5.23.70.sh

set -e

echo "=== Omaha OntoCenter 自动部署 ==="
echo "服务器: 69.5.23.70"
echo "开始时间: $(date)"
echo ""

# 数据库密码（自动生成）
DB_PASSWORD="omaha_$(openssl rand -hex 16)"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)
TUSHARE_TOKEN="044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90"

echo "步骤 1/9: 更新系统..."
apt update -qq && apt upgrade -y -qq

echo "步骤 2/9: 安装基础软件..."
apt install -y -qq python3.10 python3.10-venv python3-pip postgresql postgresql-contrib nginx git curl

echo "步骤 3/9: 配置 PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql

sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS omaha_cloud;
DROP USER IF EXISTS omaha;
CREATE DATABASE omaha_cloud;
CREATE USER omaha WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE omaha_cloud TO omaha;
ALTER DATABASE omaha_cloud OWNER TO omaha;
\q
EOF

echo "PostgreSQL 配置完成"

echo "步骤 4/9: 部署应用代码..."
rm -rf /opt/omaha-cloud
mkdir -p /opt/omaha-cloud
cp -r /tmp/omaha_ontocenter/* /opt/omaha-cloud/

echo "步骤 5/9: 配置 Python 环境..."
cd /opt/omaha-cloud
python3.10 -m venv venv
source venv/bin/activate
cd backend
pip install -q -r requirements.txt

echo "步骤 6/9: 配置环境变量..."
cat > /opt/omaha-cloud/backend/.env << EOF
DATABASE_URL=postgresql://omaha:$DB_PASSWORD@localhost/omaha_cloud
SECRET_KEY=$SECRET_KEY
TUSHARE_TOKEN=$TUSHARE_TOKEN
ACCESS_TOKEN_EXPIRE_MINUTES=43200
EOF

echo "环境变量配置完成"

echo "步骤 7/9: 初始化数据库..."
cd /opt/omaha-cloud/backend
source ../venv/bin/activate
alembic upgrade head

python scripts/generate_invite_codes.py --count 10 > /root/invite_codes.txt
echo "邀请码已保存到 /root/invite_codes.txt"

echo "步骤 8/9: 配置 systemd 服务..."
cat > /etc/systemd/system/omaha-cloud.service << 'EOF'
[Unit]
Description=Omaha Cloud API Service
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/omaha-cloud/backend
Environment="PATH=/opt/omaha-cloud/venv/bin"
ExecStart=/opt/omaha-cloud/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable omaha-cloud
systemctl start omaha-cloud

echo "应用服务已启动"

echo "步骤 9/9: 配置 Nginx..."
cat > /etc/nginx/sites-available/omaha-cloud << 'EOF'
server {
    listen 80;
    server_name 69.5.23.70;

    location /api/public/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

ln -sf /etc/nginx/sites-available/omaha-cloud /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo "=== 部署完成 ==="
echo "API 地址: http://69.5.23.70/api/public/v1"
echo "邀请码: cat /root/invite_codes.txt"
echo "服务状态: systemctl status omaha-cloud"
echo "查看日志: journalctl -u omaha-cloud -f"
echo ""
echo "数据库密码已保存到: /root/db_password.txt"
echo "$DB_PASSWORD" > /root/db_password.txt
chmod 600 /root/db_password.txt
