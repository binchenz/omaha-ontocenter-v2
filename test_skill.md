# Financial Ontology Skill 测试报告

## 测试环境

- **项目**: 测试1 (Project ID: 7)
- **API Key**: 存在且活跃 (Prefix: d65f7f9d)
- **配置**: 已加载 ontology config
- **数据库**: SQLite (backend/omaha.db)

## Skill 文件结构

```
.claude/skills/financial-ontology/
├── SKILL.md           ✅ 已创建
├── examples.md        ✅ 已创建
├── mcp-setup.md       ✅ 已创建
└── README.md          ✅ 已创建
```

## 测试步骤

### 1. 配置 MCP Server

由于 API key 已被哈希，需要生成新的 key 用于测试。

**方法 1: 通过 API 生成**
```bash
# 启动后端
cd backend
uvicorn app.main:app --reload

# 使用 API 生成 key
curl -X POST http://localhost:8000/api/v1/projects/7/api-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "MCP Test Key"}'
```

**方法 2: 通过数据库直接创建**
```python
# 运行此脚本生成测试 key
python backend/scripts/generate_api_key.py --project-id 7
```

### 2. 配置 MCP

将生成的 API key 添加到 `.claude/settings/mcp.json`:

```json
{
  "mcpServers": {
    "omaha-ontocenter": {
      "command": "python",
      "args": ["-m", "app.mcp.server"],
      "cwd": "/Users/wangfushuaiqi/omaha_ontocenter/backend",
      "env": {
        "OMAHA_API_KEY": "omaha_1_xxxxx",
        "DATABASE_URL": "sqlite:///./omaha.db",
        "SECRET_KEY": "your-secret-key-here-change-in-production-min-32-chars",
        "DATAHUB_GMS_URL": "http://localhost:8080"
      }
    }
  }
}
```

### 3. 测试查询

重启 Claude Code 后，测试以下查询：

**测试 1: 列出对象**
```
使用 financial-ontology skill 列出所有可用的业务对象
```

**测试 2: 查询股票**
```
查找所有银行股
```

**测试 3: 财务指标**
```
查询平安银行的市盈率和ROE
```

## 预期结果

1. MCP server 成功连接
2. 可以列出 Stock, FinancialIndicator, BalanceSheet 等对象
3. 查询返回格式化的数据（货币、百分比等）
4. 支持过滤和关联查询

## 注意事项

- API key 只在生成时显示一次，需要立即保存
- 确保 backend 依赖已安装 (`pip install -r requirements.txt`)
- MCP server 需要访问数据库文件
- 测试前确保项目有有效的 ontology 配置
