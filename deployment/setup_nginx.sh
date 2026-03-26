#!/bin/bash
# Nginx 和 SSL 配置脚本

set -e

echo "=== 配置 Nginx 和 SSL ==="
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 root 用户运行此脚本"
    exit 1
fi

# 获取域名
read -p "请输入你的域名 (例如: api.example.com): " DOMAIN

# 配置 Nginx
echo "配置 Nginx..."
cat > /etc/nginx/sites-available/omaha-cloud << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location /api/public/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# 启用站点
ln -sf /etc/nginx/sites-available/omaha-cloud /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo "Nginx 配置完成"

# 配置 SSL
echo ""
read -p "是否配置 SSL 证书? (y/n): " SETUP_SSL

if [ "$SETUP_SSL" = "y" ]; then
    echo "配置 SSL 证书..."
    read -p "请输入你的邮箱: " EMAIL

    certbot --nginx -d $DOMAIN --email $EMAIL --agree-tos --non-interactive

    echo "SSL 证书配置完成"
    echo "你的 API 地址: https://$DOMAIN/api/public/v1"
else
    echo "跳过 SSL 配置"
    echo "你的 API 地址: http://$DOMAIN/api/public/v1"
fi

echo ""
echo "=== Nginx 配置完成 ==="
echo ""
echo "下一步: 配置定时任务"
echo "运行: bash /opt/omaha-cloud/deployment/setup_cron.sh"
