# 金融分析系统云端部署设计文档

**日期**: 2026-03-27
**作者**: 用户 + Claude Sonnet 4.6
**状态**: 设计阶段

## 1. 项目概述

### 1.1 目标

将 Omaha OntoCenter 金融分析系统部署到火山引擎云服务器，通过 REST API 对外提供服务，让其他用户可以通过安装 Claude Code Skill 来使用这个系统进行 A 股金融数据查询和分析。

### 1.2 核心特性

- **邀请码系统**: 通过邀请码控制用户注册，管理用户增长
- **数据公开**: 所有查询和分析结果公开，形成知识共享社区
- **REST API**: 标准的 HTTP API，易于集成和使用
- **单体架构**: 初期采用简单的单服务器部署，成本可控
- **定时缓存**: 热门数据定时缓存，减少 Tushare API 调用

### 1.3 用户体验

用户通过以下步骤使用系统：
1. 获取邀请码
2. 注册账号并获取 API Key
3. 安装 financial-ontology-cloud skill
4. 在 Claude Code 中使用自然语言查询金融数据

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    用户的 Claude Code                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Financial Ontology Skill                            │   │
│  │  - 查询模板                                           │   │
│  │  - API 调用示例                                       │   │
│  │  - 结果格式化                                         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS (REST API)
                            │ Authorization: Bearer {api_key}
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              火山引擎云服务器 (单台)                          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Nginx (反向代理 + HTTPS)                          │    │
│  └────────────────────────────────────────────────────┘    │
│                            │                                 │
│  ┌────────────────────────────────────────────────────┐    │
│  │  FastAPI 应用                                       │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │  公开 API 端点                                │  │    │
│  │  │  - POST /api/public/query                    │  │    │
│  │  │  - GET  /api/public/objects                  │  │    │
│  │  │  - GET  /api/public/schema/{object}          │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │  邀请码系统                                   │  │    │
│  │  │  - POST /api/auth/register (邀请码)          │  │    │
│  │  │  - POST /api/auth/exchange (换 API Key)      │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────┘    │
│                            │                                 │
│  ┌────────────────────────────────────────────────────┐    │
│  │  PostgreSQL 数据库                                  │    │
│  │  - users (用户表)                                   │    │
│  │  - invite_codes (邀请码表)                          │    │
│  │  - api_keys (API Key 表)                           │    │
│  │  - cached_stocks (缓存的股票数据)                   │    │
│  │  - cached_financial (缓存的财务数据)                │    │
│  │  - query_logs (查询日志 - 公开)                     │    │
│  └────────────────────────────────────────────────────┘    │
│                            │                                 │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Cron 定时任务                                      │    │
│  │  - 每天凌晨同步股票基本信息                          │    │
│  │  - 每天凌晨同步财务报表数据                          │    │
│  │  - 每天开盘前同步行业分类                            │    │
│  └────────────────────────────────────────────────────┘    │
│                            │                                 │
│                            ▼                                 │
│                    Tushare Pro API                          │
│                  (按需调用 + 定时缓存)                       │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

- **Web 服务器**: Nginx (反向代理 + SSL)
- **应用框架**: FastAPI (Python)
- **数据库**: PostgreSQL 14+
- **定时任务**: Cron
- **数据源**: Tushare Pro API
- **部署平台**: 火山引擎云服务器

## 3. 数据模型设计

### 3.1 核心数据表

#### users - 用户表
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invited_by INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE
);
```

#### invite_codes - 邀请码表
```sql
CREATE TABLE invite_codes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) UNIQUE NOT NULL,
    created_by INTEGER REFERENCES users(id),
    used_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP,
    is_used BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP
);
```

#### api_keys - API Key 表
```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    key_hash VARCHAR(64) NOT NULL,
    key_prefix VARCHAR(8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

#### public_query_logs - 查询日志表（公开）
```sql
CREATE TABLE public_query_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    query_type VARCHAR(50),
    object_type VARCHAR(50),
    filters JSONB,
    result_count INTEGER,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_public BOOLEAN DEFAULT TRUE
);
```

#### cached_stocks - 缓存股票数据
```sql
CREATE TABLE cached_stocks (
    ts_code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(50),
    industry VARCHAR(50),
    area VARCHAR(50),
    market VARCHAR(20),
    list_date VARCHAR(8),
    list_status VARCHAR(1),
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_industry ON cached_stocks(industry);
CREATE INDEX idx_area ON cached_stocks(area);
```

#### cached_financial_indicators - 缓存财务指标
```sql
CREATE TABLE cached_financial_indicators (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(20),
    end_date VARCHAR(8),
    roe DECIMAL(10,2),
    roa DECIMAL(10,2),
    grossprofit_margin DECIMAL(10,2),
    netprofit_margin DECIMAL(10,2),
    debt_to_assets DECIMAL(10,2),
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ts_code ON cached_financial_indicators(ts_code);
CREATE INDEX idx_end_date ON cached_financial_indicators(end_date);
```

### 3.2 数据缓存策略

| 数据类型 | 更新频率 | 缓存时长 | 说明 |
|---------|---------|---------|------|
| 股票基本信息 | 每天 1 次 | 永久 | 变化很少 |
| 行业分类 | 每天 1 次 | 永久 | 基本不变 |
| 财务指标 | 每天 1 次 | 永久 | 季度更新 |
| 资产负债表 | 每天 1 次 | 永久 | 季度更新 |
| 现金流量表 | 每天 1 次 | 永久 | 季度更新 |
| 日线行情 | 按需查询 | 不缓存 | 实时性要求高 |

### 3.3 数据同步流程

```
每天凌晨 2:00
├─ 同步股票基本信息（约 5000 条）
├─ 同步行业分类（约 100 条）
└─ 同步最新财务数据（增量更新）

用户查询时
├─ 基础数据 → 从缓存读取
├─ 实时数据 → 调用 Tushare API
└─ 记录查询日志（公开）
```

## 4. API 设计

### 4.1 基础信息

- **基础 URL**: `https://your-domain.com/api/public/v1`
- **认证方式**: `Authorization: Bearer {api_key}`
- **响应格式**: JSON
- **字符编码**: UTF-8

### 4.2 公开 API 端点（需要 API Key）

#### 4.2.1 查询对象列表
```http
GET /objects

响应:
{
  "success": true,
  "objects": [
    {"name": "Stock", "description": "A股上市公司基本信息"},
    {"name": "FinancialIndicator", "description": "财务指标数据"}
  ]
}
```

#### 4.2.2 获取对象 Schema
```http
GET /schema/{object_type}

示例: GET /schema/Stock

响应:
{
  "success": true,
  "object_type": "Stock",
  "fields": [
    {"name": "ts_code", "type": "string", "description": "股票代码"},
    {"name": "name", "type": "string", "description": "股票名称"}
  ]
}
```

#### 4.2.3 查询数据（核心端点）
```http
POST /query

请求体:
{
  "object_type": "Stock",
  "selected_columns": ["ts_code", "name", "industry"],
  "filters": [
    {"field": "industry", "operator": "=", "value": "银行"}
  ],
  "limit": 20
}

响应:
{
  "success": true,
  "data": [
    {"ts_code": "000001.SZ", "name": "平安银行", "industry": "银行"}
  ],
  "count": 1,
  "cached": true,
  "execution_time_ms": 15
}
```

#### 4.2.4 查看公开查询日志
```http
GET /queries/recent?limit=50

响应:
{
  "success": true,
  "queries": [
    {
      "id": 123,
      "user": "user_abc",
      "query_type": "stock",
      "filters": {...},
      "result_count": 5,
      "created_at": "2024-03-27T10:00:00Z"
    }
  ]
}
```

#### 4.2.5 查看热门查询
```http
GET /queries/popular?days=7

响应:
{
  "success": true,
  "popular_queries": [
    {
      "query_pattern": "查询银行股",
      "count": 45,
      "example": {...}
    }
  ]
}
```

### 4.3 认证相关端点（无需 API Key）

#### 4.3.1 注册（使用邀请码）
```http
POST /auth/register

请求体:
{
  "invite_code": "ABC123XYZ",
  "username": "user123",
  "email": "user@example.com"
}

响应:
{
  "success": true,
  "user_id": 42,
  "message": "注册成功，请使用 /auth/api-key 获取 API Key"
}
```

#### 4.3.2 获取 API Key
```http
POST /auth/api-key

请求体:
{
  "username": "user123",
  "email": "user@example.com"
}

响应:
{
  "success": true,
  "api_key": "omaha_pub_abc123...",
  "message": "请妥善保管此 API Key，不会再次显示"
}
```

### 4.4 API 限流策略

| 端点类型 | 限制 | 说明 |
|---------|------|------|
| 查询端点 | 100 次/小时/用户 | 防止滥用 |
| Schema 端点 | 无限制 | 轻量级查询 |
| 认证端点 | 5 次/小时/IP | 防止暴力破解 |

## 5. Skill 实现方案

### 5.1 Skill 文件结构

```
financial-ontology-cloud/
├── SKILL.md              # 主文档
├── examples.md           # 查询示例
├── setup.md              # 设置指南
└── README.md             # 快速入门
```

### 5.2 用户使用流程

1. **获取邀请码**: 联系管理员获取邀请码
2. **注册账号**: 使用邀请码注册
3. **获取 API Key**: 注册后获取 API Key
4. **安装 Skill**: 下载 Skill 文件到 `.claude/skills/` 目录
5. **配置 API Key**: 设置环境变量 `OMAHA_CLOUD_API_KEY`
6. **开始使用**: 在 Claude Code 中使用自然语言查询

### 5.3 查询示例

**用户输入**: "查找市盈率低于 15 的银行股"

**Claude 执行**:
```bash
curl -X POST https://your-domain.com/api/public/v1/query \
  -H "Authorization: Bearer $OMAHA_CLOUD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "Stock",
    "selected_columns": ["ts_code", "name", "industry"],
    "joins": [{
      "object_type": "FinancialIndicator",
      "join_field": "ts_code",
      "selected_columns": ["pe", "roe"]
    }],
    "filters": [
      {"field": "industry", "operator": "=", "value": "银行"},
      {"field": "FinancialIndicator.pe", "operator": "<", "value": 15}
    ],
    "limit": 20
  }'
```

**展示结果**:
```
找到 3 只符合条件的银行股：

1. 平安银行 (000001.SZ)
   - 市盈率: 12.5
   - ROE: 15.8%

2. 招商银行 (600036.SH)
   - 市盈率: 14.2
   - ROE: 18.3%

3. 兴业银行 (601166.SH)
   - 市盈率: 13.8
   - ROE: 16.5%
```

### 5.4 Skill 分发方式

1. **GitHub 仓库**: 用户克隆到本地 `.claude/skills/` 目录
2. **直接下载**: 提供 ZIP 包下载
3. **Skill 市场**: 未来可能发布到 Claude Code Skill 市场

## 6. 部署方案

### 6.1 服务器配置

**推荐配置**:
- **实例类型**: 通用型 g3i.large
- **CPU/内存**: 2核4GB
- **存储**: 40GB SSD 系统盘 + 100GB 数据盘
- **带宽**: 5Mbps
- **操作系统**: Ubuntu 22.04 LTS
- **预估成本**: ¥150-200/月

### 6.2 部署步骤

**Phase 1: 服务器初始化（1天）**
1. 购买火山引擎服务器
2. 配置安全组（开放 80, 443 端口）
3. 安装基础软件（Python 3.10, PostgreSQL, Nginx）
4. 配置 SSL 证书（Let's Encrypt）

**Phase 2: 应用部署（2-3天）**
1. 克隆代码到服务器
2. 修改后端代码，添加公开 API 端点
3. 配置数据库和环境变量
4. 部署 FastAPI 应用（使用 systemd）
5. 配置 Nginx 反向代理

**Phase 3: 数据同步（1天）**
1. 编写数据同步脚本
2. 配置 cron 定时任务
3. 首次全量同步数据
4. 验证数据完整性

**Phase 4: Skill 开发（1-2天）**
1. 创建 Skill 文件
2. 编写使用文档和示例
3. 本地测试 Skill
4. 发布到 GitHub

**Phase 5: 测试和上线（2-3天）**
1. 生成测试邀请码
2. 邀请 5-10 个用户内测
3. 收集反馈并优化
4. 正式上线

**总计时间**: 约 1-2 周

### 6.3 目录结构

```
/opt/omaha-cloud/
├── backend/              # FastAPI 应用
├── nginx/               # Nginx 配置
├── scripts/             # 部署和维护脚本
│   ├── sync_data.sh    # 数据同步脚本
│   └── backup.sh       # 备份脚本
├── logs/               # 日志文件
└── .env                # 环境变量
```

### 6.4 关键配置

#### systemd 服务配置
```ini
[Unit]
Description=Omaha Cloud API Service
After=network.target postgresql.service

[Service]
Type=simple
User=omaha
WorkingDirectory=/opt/omaha-cloud/backend
Environment="PATH=/opt/omaha-cloud/venv/bin"
ExecStart=/opt/omaha-cloud/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Nginx 配置
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location /api/public/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Crontab 配置
```cron
# 每天凌晨 2:00 同步数据
0 2 * * * /opt/omaha-cloud/scripts/sync_data.sh

# 每天凌晨 3:00 备份数据库
0 3 * * * /opt/omaha-cloud/scripts/backup.sh
```

## 7. 监控和维护

### 7.1 基础监控

- 服务器资源监控（CPU、内存、磁盘）
- API 响应时间和错误率
- 数据库连接数和查询性能
- Tushare API 调用次数

### 7.2 日志管理

- 应用日志：`/opt/omaha-cloud/logs/app.log`
- Nginx 日志：`/var/log/nginx/access.log`
- 数据同步日志：`/opt/omaha-cloud/logs/sync.log`

### 7.3 备份策略

- 数据库每天备份一次
- 保留最近 7 天的备份
- 重要数据异地备份

## 8. 安全考虑

### 8.1 认证和授权

- API Key 使用 SHA256 哈希存储
- HTTPS 加密传输
- API 限流防止滥用
- 邀请码系统控制用户增长

### 8.2 数据安全

- 定期备份数据库
- 敏感信息加密存储
- 日志脱敏处理

### 8.3 网络安全

- 配置防火墙规则
- 只开放必要端口（80, 443）
- 定期更新系统补丁

## 9. 扩展性考虑

虽然初期采用单体架构，但设计时考虑了未来扩展：

### 9.1 水平扩展

- API 服务无状态，可以轻松添加多个实例
- 使用负载均衡器分发请求
- 数据库可以升级为主从复制

### 9.2 垂直扩展

- 服务器配置可以按需升级
- 数据库可以升级到更高配置

### 9.3 功能扩展

- 添加 Redis 缓存层
- 引入消息队列处理异步任务
- 添加更多数据源

## 10. 成本估算

### 10.1 初期成本（月）

| 项目 | 费用 |
|------|------|
| 云服务器（2核4G） | ¥150 |
| 数据盘（100GB） | ¥30 |
| 带宽（5Mbps） | ¥20 |
| 域名 | ¥10 |
| **总计** | **¥210** |

### 10.2 运营成本

- Tushare Pro API: 根据账号级别，可能需要升级
- 人力成本: 初期维护约 2-4 小时/周

## 11. 风险和应对

### 11.1 技术风险

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| Tushare API 限制 | 查询失败 | 增加缓存、升级账号 |
| 服务器故障 | 服务中断 | 定期备份、快速恢复 |
| 数据库性能 | 查询变慢 | 优化索引、升级配置 |

### 11.2 业务风险

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 用户增长过快 | 服务器压力 | 邀请码控制、扩容 |
| 数据合规问题 | 法律风险 | 明确数据使用协议 |
| 滥用风险 | 资源浪费 | API 限流、监控告警 |

## 12. 后续优化方向

### 12.1 短期（1-3个月）

- 添加用户使用统计
- 优化查询性能
- 完善文档和示例

### 12.2 中期（3-6个月）

- 添加 Redis 缓存
- 引入消息队列
- 开发 Web 管理界面

### 12.3 长期（6-12个月）

- 支持更多数据源
- 开发移动应用
- 建立用户社区

## 13. 总结

本设计采用 MVP（最小可行产品）方案，通过简单的单体架构快速验证想法。核心特点包括：

1. **快速上线**: 1-2 周内可以部署完成
2. **成本可控**: 初期月成本约 ¥200
3. **易于维护**: 架构简单，便于调试和优化
4. **可扩展**: 设计时考虑了未来扩展路径

通过邀请码系统控制用户增长，通过定时缓存减少 API 调用，通过公开查询日志形成知识共享社区。这个方案平衡了功能、成本和复杂度，适合初期验证和迭代。
