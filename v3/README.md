# OntoCenter v3

AI 原生的中小企业数据分析平台 — "面向中国 SME 的 Palantir"。

- **Python FastAPI** — 数据摄入、本体引擎、OAG 查询、MCP Server
- **Next.js 14** — BFF + UI + LLM Agent (Vercel AI SDK)
- **Delta Lake + DuckDB** — 数据版本化 + 列式查询
- **PostgreSQL / SQLite** — 元数据存储

## 快速开始

### 依赖
- Python 3.12+
- Node.js 22+
- LLM API Key（DeepSeek / OpenAI / Anthropic 任选）

### 1. 启动后端

```bash
cd v3/python-api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

后端跑在 `http://localhost:8000`，API 文档 `http://localhost:8000/docs`。

### 2. 配置 LLM

在 `v3/nextjs/.env.local` 中设置：

```bash
# DeepSeek（推荐，国内可直连）
OPENAI_API_KEY=sk-your-deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# 或 OpenAI
# OPENAI_API_KEY=sk-...
# OPENAI_BASE_URL=https://api.openai.com/v1
# LLM_MODEL=gpt-4o-mini

PYTHON_API_URL=http://127.0.0.1:8000
NEXTAUTH_SECRET=dev-secret
NEXTAUTH_URL=http://localhost:3000
```

### 3. 启动前端

```bash
cd v3/nextjs
npm install
NO_PROXY=localhost,127.0.0.1 npm run dev
```

前端跑在 `http://localhost:3000`，登录用 `demo@ontocenter.dev / demo123`。

## 典型流程

1. **接入数据** — `/datasources/upload` 上传 CSV，或 `/datasources/connect` 连接 MySQL/PostgreSQL
2. **创建本体** — 自动生成 YAML 或在 `/ontology/create` 手写
3. **Chat 分析** — `/chat` 用自然语言提问，Agent 自动选工具查询 + 生成图表
4. **导出 MCP** — `/skills` 生成 MCP 配置给 Claude Code 安装

## 测试

```bash
cd v3/python-api && source .venv/bin/activate && pytest
# 17 passed

cd v3/nextjs && npx tsc --noEmit
# TS: PASS
```

## 部署

**Docker Compose**（本地部署）：
```bash
cd v3 && docker compose up -d
```

**Railway**（SaaS）：
```bash
railway up
```

## 架构

```
用户 → Next.js BFF → LLM (Planner + ReAct) → Python API → DuckDB + Delta Lake
                                              ↓
                                        MCP Runtime (HTTP JSON-RPC)
                                              ↑
                                        Claude Code / 其他 Agent
```

## 项目结构

```
v3/
├── python-api/        # FastAPI + SQLAlchemy + Delta Lake
│   ├── app/api/       # 端点：ingest/ontology/mcp/datasources
│   ├── app/services/  # 本体引擎/查询/MCP 工厂
│   ├── app/connectors/  # CSV/SQLite/MySQL/PostgreSQL
│   └── tests/         # 17 个 E2E 测试
└── nextjs/            # Next.js App Router + Tailwind + shadcn/ui
    ├── src/app/       # 路由 + agent + API routes
    ├── src/components/  # Chat UI + ChartView
    └── src/services/  # pythonApi 客户端
```

## License

MIT
