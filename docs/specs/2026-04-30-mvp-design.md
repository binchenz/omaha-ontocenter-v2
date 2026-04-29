# Omaha OntoCenter MVP Design — 中小企业 AI 语义层

Date: 2026-04-30

## Vision

Omaha OntoCenter = 中小企业的 Palantir Ontology。

让每个中小企业拥有自己的语义数据层：AI 自动理解业务对象和关系，通过自然语言查询数据，并通过 MCP/Skill 让任何外部 AI Agent 消费企业的业务知识。

## Differentiation

本体语义理解 + 零门槛 AI 对话 + 多源数据融合 + MCP 开放生态。四合一，市面无竞品同时覆盖。

## Business Model

开源核心（AGPL/BSL）+ 私有化部署。类 GitLab 模式。

## Target Users

所有阶段的中小企业：Excel 管理型、有 ERP 型、SaaS 散落型。第一批用户不限行业。

---

## MVP Scope

### In Scope

1. **数据接入**：CSV/Excel 上传 + MySQL/PostgreSQL 连接配置 UI
2. **AI 建模**：上传数据后 AI 自动推断本体（对象、属性、关系、数据质量）
3. **自然语言查询**：多轮对话、跨对象分析、聚合统计
4. **MCP Server**：完整本体工具集，可被 Claude Code / GPT / 任意 Agent 调用
5. **本体可视化**：可交互的对象关系图
6. **基础权限**：管理员/成员两个角色
7. **查询导出**：CSV/Excel 下载
8. **私有化部署**：一键 docker-compose 部署 + 初始化向导
9. **开源准备**：LICENSE、Contributing Guide、Demo 数据

### Out of Scope (Deferred)

- 多租户 SaaS 版本
- 实时数据同步（CDC）
- 定时任务/告警规则
- 数据血缘可视化
- API 市场 / Skill 市场
- 移动端适配
- 国际化（i18n）

---

## Phase 1: Product Hardening (Week 1-2)

### 1.1 Error Handling Standardization

**Current state:** Generic 500 errors, inconsistent error formats.

**Target:**
- Unified error response schema: `{code: string, message: string, detail?: any}`
- Error codes by domain: `AUTH_001`, `QUERY_001`, `ONTOLOGY_001`, etc.
- User-friendly Chinese error messages for all client-facing errors
- Backend exception hierarchy: `AppError` → `AuthError`, `QueryError`, `OntologyError`

**Files to modify:**
- `backend/app/schemas/error.py` — extend ErrorResponse
- `backend/app/main.py` — exception handlers per error type
- All API route files — replace bare HTTPException with typed errors

### 1.2 Data Source Connection UI

**Current state:** Backend connectors exist (MySQL, PostgreSQL, SQLite). No frontend UI to configure them.

**Target:**
- New page: "数据源管理" accessible from project settings
- Form to add a data source: type selector → connection params → test connection → save
- Supported types: MySQL, PostgreSQL, SQLite (file path), CSV/Excel (upload)
- Connection test endpoint: `POST /api/v1/datasources/test`
- Saved datasources stored per-project in database

**New backend components:**
- `app/models/project/datasource.py` — Datasource model (project_id, type, connection_json, name, status)
- `app/api/projects/datasources.py` — CRUD + test endpoint
- `app/schemas/project/datasource.py` — request/response schemas

**New frontend components:**
- `pages/apps/DatasourcePage.tsx` — list + add/edit/delete datasources
- `components/datasource/ConnectionForm.tsx` — type-specific form fields
- `services/datasourceService.ts` — API client

### 1.3 MCP Server Completion

**Current state:** Basic MCP server with list_objects, get_schema, query_data, get_relationships. Uses module-level `query_engine` singleton (no project context).

**Target:**
- Project-aware MCP: tools operate within a specific project's ontology
- Full tool set:
  - `list_objects` — list all business objects in the ontology
  - `get_schema(object_type)` — get fields and semantic types
  - `search(object_type, filters?, columns?, limit?)` — query data
  - `count(object_type, group_by?, filters?)` — aggregation
  - `get_relationships(object_type)` — list relationships
  - `navigate(from_object, from_id, path)` — multi-hop navigation
- Authentication: API key-based (reuse existing api_keys system)
- Documentation: tool descriptions in Chinese for LLM consumption

**Files to modify:**
- `backend/app/mcp/server.py` — add project context, auth
- `backend/app/mcp/tools.py` — expand tool set
- `.mcp.json` — update configuration

---

## Phase 2: Experience Polish (Week 3-4)

### 2.1 Ontology Graph Visualization

**Current state:** `OntologyGraph.tsx` exists but unclear interactivity level.

**Target:**
- Force-directed graph showing objects as nodes, relationships as edges
- Click node → show properties panel
- Click edge → show relationship details
- Color coding by domain/datasource
- Zoom, pan, fit-to-screen controls
- Library: use existing ECharts (already in deps) or D3.js

### 2.2 Query Result Export

**Target:**
- "导出" button on query results
- Formats: CSV, Excel (.xlsx)
- Backend endpoint: `POST /api/v1/chat/{project_id}/sessions/{session_id}/export`
- Returns file download with proper Content-Disposition header

### 2.3 Frontend UX Hardening

**Target:**
- Loading skeletons for all data-fetching states
- Error boundaries with retry buttons
- Empty states with guidance ("还没有数据源，点击添加")
- Toast notifications for success/error actions
- Responsive sidebar collapse on narrow screens

---

## Phase 3: Permissions + Deployment (Week 5-6)

### 3.1 Basic RBAC

**Current state:** Only owner_id check. No roles.

**Target:**
- Two roles: `admin` (full access) and `member` (read + query, no delete/config)
- Role stored on `ProjectMember` model (already exists, add `role` field)
- Permission check decorator/dependency for API routes
- Frontend: hide admin-only actions for members

**Scope:**
- Project-level roles only (no org-level)
- Admin can: manage datasources, delete project, manage members, confirm ontology
- Member can: query, view ontology, export results

### 3.2 Production Hardening

**Target:**
- Rate limiting: 60 req/min per user for API, 10 req/min for LLM calls
- CORS: configurable via environment variable (not hardcoded)
- Health check: add LLM connectivity check (ping with minimal prompt)
- Graceful shutdown: drain in-flight requests on SIGTERM
- Request ID: propagate through all log entries

### 3.3 One-Click Deployment

**Target:**
- `./deploy.sh` script that:
  1. Checks prerequisites (Docker, docker-compose)
  2. Generates `.env` with random SECRET_KEY
  3. Prompts for LLM API key
  4. Runs `docker-compose up -d`
  5. Runs database migrations
  6. Creates initial admin user
  7. Prints access URL
- Works on: Ubuntu 20.04+, CentOS 7+, macOS (for dev)

---

## Phase 4: Open Source Preparation (Week 7-8)

### 4.1 License

**Decision:** AGPL-3.0 (strong copyleft, requires derivative works to be open source; commercial exception available for enterprise customers who want proprietary modifications).

**Rationale:** Protects against cloud providers hosting without contributing back. Enterprise customers who need proprietary deployment buy a commercial license.

### 4.2 Open Source Documentation

- `README.md` — already updated (done)
- `CONTRIBUTING.md` — how to contribute, code style, PR process
- `docs/architecture.md` — system architecture overview for contributors
- `docs/deployment-guide.md` — detailed deployment instructions
- Demo dataset + seed script for quick evaluation

### 4.3 Release Preparation

- GitHub Release with changelog
- Demo video (2-3 min): upload → model → query → MCP
- Landing page content (can be a simple GitHub Pages site)
- Social media announcement (Twitter/X, V2EX, 掘金)

---

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Graph library | ECharts (graph type) | Already in deps, good Chinese docs, sufficient for MVP |
| Rate limiter | slowapi (FastAPI) | Lightweight, no Redis dependency for MVP |
| RBAC storage | role field on ProjectMember | Simplest; no separate permissions table needed for 2 roles |
| Export format | openpyxl for xlsx | Already indirect dep via pandas; lightweight |
| MCP auth | API key in header | Reuses existing api_keys infrastructure |
| Deployment | docker-compose only | No K8s for MVP; single-server is fine for SME |

## Success Criteria

1. A new user can go from `docker-compose up` to querying their data in under 10 minutes
2. MCP tools are callable from Claude Code with zero additional configuration
3. The ontology graph clearly shows object relationships at a glance
4. Error messages are actionable (user knows what to do next)
5. A 3-person team can collaborate on the same project with appropriate permissions
