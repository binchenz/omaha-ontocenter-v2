# Omaha OntoCenter 云服务器部署指南

## 快速部署

已为你准备好三个自动化部署脚本，按顺序执行即可：

### 1. 服务器初始化和应用部署

```bash
# 上传代码到服务器
scp -r /path/to/omaha_ontocenter root@your-server-ip:/tmp/

# SSH 登录服务器
ssh root@your-server-ip

# 运行部署脚本
cd /tmp/omaha_ontocenter/deployment
bash setup_server.sh
```

这个脚本会：
- 安装 Python、PostgreSQL、Nginx、Git
- 创建数据库和用户
- 克隆代码并安装依赖
- 配置环境变量
- 初始化数据库
- 生成 10 个邀请码
- 启动应用服务

### 2. 配置 Nginx 和 SSL

```bash
bash setup_nginx.sh
```

这个脚本会：
- 配置 Nginx 反向代理
- 申请并配置 SSL 证书（Let's Encrypt）
- 启用 HTTPS

### 3. 配置定时任务

```bash
bash setup_cron.sh
```

这个脚本会：
- 配置每天凌晨 2:00 同步 Tushare 数据
- 配置每天凌晨 3:00 备份数据库

## 部署前准备

1. **域名解析**: 将域名 A 记录指向服务器 IP
2. **Tushare Token**: 准备好你的 Tushare Pro API Token
3. **Git 仓库**: 确保代码已推送到 Git 仓库

## 部署后验证

```bash
# 检查服务状态
systemctl status omaha-cloud

# 查看日志
journalctl -u omaha-cloud -f

# 测试 API
curl https://your-domain.com/api/public/v1/objects
```

## 获取邀请码

```bash
cat /root/invite_codes.txt
```

## 常用命令

```bash
# 重启服务
systemctl restart omaha-cloud

# 查看日志
journalctl -u omaha-cloud -n 100

# 手动同步数据
cd /opt/omaha-cloud/backend
source ../venv/bin/activate
python scripts/sync_tushare_data.py

# 生成更多邀请码
python scripts/generate_invite_codes.py --count 5
```

## 目录结构

```
/opt/omaha-cloud/
├── backend/           # 后端代码
├── venv/             # Python 虚拟环境
├── deployment/       # 部署脚本
└── logs/            # 日志文件（自动创建）
```

## 故障排查

### 服务无法启动

```bash
# 查看详细错误
journalctl -u omaha-cloud -n 50

# 检查配置文件
cat /opt/omaha-cloud/backend/.env

# 手动启动测试
cd /opt/omaha-cloud/backend
source ../venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 状态
systemctl status postgresql

# 测试数据库连接
psql -U omaha -d omaha_cloud -h localhost
```

### SSL 证书问题

```bash
# 重新申请证书
certbot --nginx -d your-domain.com --force-renewal
```
