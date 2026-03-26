#!/bin/bash
# 配置定时任务脚本

set -e

echo "=== 配置定时任务 ==="
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 root 用户运行此脚本"
    exit 1
fi

# 配置数据同步脚本
echo "配置数据同步任务..."
chmod +x /opt/omaha-cloud/deployment/sync_wrapper.sh
chmod +x /opt/omaha-cloud/deployment/backup.sh

# 添加到 crontab
(crontab -l 2>/dev/null; cat /opt/omaha-cloud/deployment/crontab.txt) | crontab -

echo "定时任务配置完成"
echo ""
echo "=== 所有配置完成 ==="
echo ""
echo "服务状态检查:"
systemctl status omaha-cloud --no-pager
echo ""
echo "查看邀请码: cat /root/invite_codes.txt"
echo "查看日志: journalctl -u omaha-cloud -f"
