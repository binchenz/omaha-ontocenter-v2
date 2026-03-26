#!/bin/bash
# 通过控制台Web终端执行的完整部署脚本
# 复制整个脚本到火山引擎控制台的Web终端执行

set -e

echo "=== Omaha OntoCenter 一键部署 ==="
echo "开始时间: $(date)"

# 配置变量
DB_PASSWORD="omaha_$(openssl rand -hex 16)"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)
TUSHARE_TOKEN="044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90"

echo "步骤 1/10: 更新系统..."
apt update -qq

echo "步骤 2/10: 安装基础软件..."
apt install -y python3.10 python3.10-venv python3-pip postgresql postgresql-contrib nginx git curl

echo "步骤 3/10: 启动 PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql
sleep 2

echo "步骤 4/10: 配置数据库..."
sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS omaha_cloud;
DROP USER IF EXISTS omaha;
CREATE DATABASE omaha_cloud;
CREATE USER omaha WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE omaha_cloud TO omaha;
ALTER DATABASE omaha_cloud OWNER TO omaha;
\q
EOF

echo "步骤 5/10: 克隆代码..."
cd /opt
rm -rf omaha-cloud
git clone https://github.com/wangfushuaiqi/omaha_ontocenter.git omaha-cloud
cd omaha-cloud

echo "步骤 6/10: 安装 Python 依赖..."
python3.10 -m venv venv
source venv/bin/activate
cd backend
pip install -q -r requirements.txt

echo "步骤 7/10: 配置环境变量..."
cat > /opt/omaha-cloud/backend/.env << EOF
DATABASE_URL=postgresql://omaha:$DB_PASSWORD@localhost/omaha_cloud
SECRET_KEY=$SECRET_KEY
TUSHARE_TOKEN=$TUSHARE_TOKEN
ACCESS_TOKEN_EXPIRE_MINUTES=43200
EOF

echo "步骤 8/10: 初始化数据库..."
alembic upgrade head
python scripts/generate_invite_codes.py --count 10 > /root/invite_codes.txt

echo "步骤 9/10: 配置 systemd 服务..."
cat > /etc/systemd/system/omaha-cloud.service << 'SVCEOF'
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
SVCEOF

systemctl daemon-reload
systemctl enable omaha-cloud
systemctl start omaha-cloud

echo "步骤 10/10: 配置 Nginx..."
cat > /etc/nginx/sites-available/omaha-cloud << 'NGXEOF'
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
NGXEOF

ln -sf /etc/nginx/sites-available/omaha-cloud /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo "=== 部署完成 ==="
echo "API 地址: http://69.5.23.70/api/public/v1"
echo ""
echo "查看邀请码: cat /root/invite_codes.txt"
echo "查看服务状态: systemctl status omaha-cloud"
echo "查看日志: journalctl -u omaha-cloud -f"
echo ""
echo "数据库密码: $DB_PASSWORD"
echo "$DB_PASSWORD" > /root/db_password.txt
chmod 600 /root/db_password.txt
