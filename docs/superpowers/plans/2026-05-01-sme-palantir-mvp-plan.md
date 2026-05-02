# MVP Implementation Plan — SME Palantir Platform

**Based on**: [Design Spec](../specs/2026-05-01-sme-palantir-design.md)
**Date**: 2026-05-01
**Team**: 2-5 people
**Target**: Deliver MVP with SaaS + Docker Compose dual deployment

---

## Phase Dependency Graph

```
Phase 0  Project Scaffold
   ↓
Phase 1  Python Core: Data Ingestion + Delta Lake
   ↓
Phase 2  Python Core: Ontology Engine + OAG Query
   ↓
Phase 3  Python Core: MCP Server Factory
                         ↘
Phase 4  Next.js Shell: Auth + Design System + Layout
   ↓
Phase 5  Next.js Shell: Agent Engine + Chat UI
   ↓
Phase 6  Integration: End-to-end Flows
   ↓
Phase 7  Deployment: Railway + Docker Compose
```

---

## Phase 0: Project Scaffold (Day 1-2)

**Goal**: Two runnable projects, shared Docker Compose, basic CI

### Tasks

**0.1 Repo structure** — Create monorepo at `platform/python-api/` + `platform/nextjs/`. Root `docker-compose.yml` with postgres, python-api, nextjs. Root `Makefile`.

**0.2 Python API scaffold** — FastAPI + uvicorn, health check endpoint. Project layout: `api/`, `services/`, `models/`, `schemas/`, `connectors/`. SQLAlchemy async + Alembic. Pytest with httpx.AsyncClient.

**0.3 Next.js scaffold** — `create-next-app` with App Router, TypeScript, Tailwind, shadcn/ui. Prisma init. Layout: `app/`, `components/`, `services/`, `types/`, `hooks/`.

**0.4 Docker Compose dev env** — postgres:16 + python-api (hot reload) + nextjs (hot reload). `.env.example` template.

**0.5 CI** — GitHub Actions: lint + typecheck + test on PR. Python (ruff, mypy, pytest), Next.js (eslint, tsc, vitest).

**Verify**: `docker compose up` → all 3 services healthy, `curl localhost:8000/health` → 200.

---

## Phase 1: Data Ingestion + Delta Lake (Day 3-7)

**Goal**: Connect to data sources, sync data into Delta Lake, query via DuckDB

### Tasks

**1.1 Connector abstraction** — `connectors/base.py` with abstract `Connector` class: `connect()`, `discover_tables()`, `sample_data(table, rows)`, `sync_table(table, delta_path)`. Implement `connectors/mysql.py`, `connectors/postgres.py`, `connectors/sqlite.py`.

**1.2 File-based ingestion** — `connectors/file.py` handles CSV/Excel upload via multipart. Stream to temp file, infer schema via pandas `read_csv`/`read_excel`, write to Delta.

**1.3 Delta Lake writer** — `services/ingest/delta_writer.py`: wraps `deltalake.write_deltalake()`. Each sync → new Delta version. Schema inference from pandas dtypes. Track metadata: `source`, `synced_at`, `row_count`.

**1.4 DuckDB query service** — `services/query/duckdb_service.py`: register Delta tables as DuckDB views. Accept SQL or structured filter dict. Return list of dicts.

**1.5 Sync scheduler** — `services/ingest/scheduler.py`: per-Dataset `sync_schedule` field (`manual`|`hourly`|`daily`|`monthly`). Async background task. Status tracking: `syncing` → `ready` | `error`.

**1.6 Ingest API endpoints** — `POST /ingest` — accept file upload or connection config. Return `IngestResponse` (tables found, fields total, sematic inference preview with confidence).

**1.7 Database models** — `DataSource` and `Dataset` SQLAlchemy models + Alembic migration. `DataSource`: type, encrypted config, status. `Dataset`: table_name, rows_count, last_synced_at, sync_schedule, status, delta_path.

**Key files created**:
```
python-api/app/
├── connectors/
│   ├── base.py           # Abstract Connector
│   ├── mysql.py
│   ├── postgres.py
│   ├── sqlite.py
│   └── file.py           # CSV/Excel
├── services/ingest/
│   ├── delta_writer.py
│   ├── scheduler.py
│   └── schema_inferrer.py
├── services/query/
│   └── duckdb_service.py
├── api/ingest.py         # POST /ingest endpoint
├── models/datasource.py
└── models/dataset.py
```

**Verify**: `POST /ingest` with a CSV → Delta table created → `SELECT COUNT(*)` via DuckDB returns correct rows.

---

## Phase 2: Ontology Engine + OAG Query (Day 8-14)

**Goal**: Define ontologies in YAML, infer from ingested data, serve OAG query responses

### Tasks

**2.1 Ontology YAML schema** — Pydantic models for ontology config: `OntologyConfig`, `ObjectDef` (name, slug, description, table_name, datasource_id), `PropertyDef` (name, slug, semantic_type, source_column, is_computed, function_ref), `LinkDef` (name, from_object, to_object, type, from_column, to_column), `FunctionDef` (name, handler, description, input_schema, output_schema, caching_ttl).

**2.2 Ontology YAML parser** — Load YAML from `configs/ontologies/`. Environment variable substitution (`${VAR_NAME}` uppercase only). Validate against Pydantic schema. Convert to internal `OntologyObject` representation.

**2.3 Ontology DB models + CRUD** — `Ontology` (tenant_id, name, slug, version, status, yaml_source), `OntologyObject`, `Property`, `Link`, `Function` SQLAlchemy models. CRUD service for full lifecycle. Alembic migration.

**2.4 Schema inference engine** — `services/ontology/inferrer.py`: scan Delta table schema, map pandas dtypes → semantic_type candidates (float64 → `number` or `currency`, datetime64 → `date`, object with low cardinality → `enum`). Generate draft YAML. LLM review for ambiguous mappings (sample values → LLM → "this looks like a price column → currency: CNY").

**2.5 OAG query engine** — `services/query/oag_service.py`:
- Accept `QueryRequest` (operation, object, filters, measures, group_by, path, limit, include_links, include_functions)
- Build DuckDB SQL from structured params
- Execute query, post-process: resolve links (second query per linked object), attach `semantic_type` metadata to each property value, attach `available_functions` per matched object
- Return `QueryResponse` with full object graph + context

**2.6 Link resolution** — `services/ontology/link_resolver.py`: for each matched result, resolve forward/reverse links. Batch query to avoid N+1 (collect target IDs, single query per link type).

**2.7 Function binding** — `services/query/function_engine.py`: dynamic import via `handler` string (e.g. `functions.risk.order_risk_scorer`). Call with matched object ID. Cache result per `caching_ttl`. Inject result into query response.

**2.8 Ontology API endpoints**:
- `GET /ontology/{id}/schema` → full ontology with objects, properties, links, functions
- `POST /ontology/{id}/query` → OAG query execution
- `GET /ontology/{id}/yaml` → export YAML
- `PUT /ontology/{id}/yaml` → update YAML (re-parse, bump version)

**2.9 Function API** — `POST /function/{name}` → execute registered function, return result

**Key files created**:
```
python-api/app/
├── schemas/
│   ├── ontology_config.py    # Pydantic: OntologyConfig, ObjectDef, etc.
│   └── query.py              # Pydantic: QueryRequest, QueryResponse
├── services/ontology/
│   ├── parser.py             # YAML → OntologyConfig
│   ├── inferrer.py           # Schema → draft YAML
│   ├── link_resolver.py      # Forward/reverse link resolution
│   └── store.py              # CRUD for ontology entities
├── services/query/
│   ├── oag_service.py        # Core OAG query engine
│   ├── query_builder.py      # Structured filter → DuckDB SQL
│   └── function_engine.py    # Dynamic import + call functions
├── api/ontology.py            # Ontology CRUD + query endpoints
├── models/
│   ├── ontology.py
│   ├── object.py
│   ├── property.py
│   ├── link.py
│   └── function.py
└── functions/                 # Built-in compute functions
    ├── __init__.py
    └── stats.py               # sum, avg, growth_rate, etc.
```

**Verify**: Ingest CSV → generate ontology draft → approve → `POST /ontology/{id}/query` returns OAG response with semantic types, links resolved, functions callable.

---

## Phase 3: MCP Server Factory (Day 15-18)

**Goal**: Auto-generate MCP Server config + tools from ontology, package as installable Skills

### Tasks

**3.1 Tool generator** — `services/mcp/tool_generator.py`: for each OntologyObject, generate standard tool definitions:
- `search_{slug}` — full-text or column-filter search
- `count_{slug}` — COUNT with optional filters
- `aggregate_{slug}` — GROUP BY with SUM/AVG/COUNT measures
- `navigate_path` — multi-hop link traversal
- `call_function` — execute registered functions

Each tool maps to OAG query engine under the hood. Tool descriptions auto-generated in Chinese from object/property descriptions.

**3.2 MCP Server runtime** — `services/mcp/server.py`: wraps mcp Python SDK. Register tools from tool_generator. Start/stop lifecycle. One server instance per ontology (one endpoint per ontology).

**3.3 Skill packager** — `services/mcp/skill_packager.py`: generate skill package following skill-creator format:
```
{slug}-skill/
├── SKILL.md              # Chinese metadata + usage examples
├── mcp-config.json       # MCP connection config (endpoint, auth)
└── examples/
    └── example-usage.md
```

**3.4 MCPServer + Skill DB models** — `MCPServer` (ontology_id, endpoint, status, port, last_accessed), `Skill` (mcp_server_id, name, version, package_url, installs_count). Alembic migration.

**3.5 MCP API endpoints**:
- `POST /ontology/{id}/mcp/generate` → create MCP Server + Skill package
- `GET /mcp/servers` → list all MCP servers
- `POST /mcp/servers/{id}/start` → start server
- `POST /mcp/servers/{id}/stop` → stop server
- `GET /skills` → list available skills
- `GET /skills/{id}/download` → download skill package

**3.6 API Key management** — `ApiKey` model (user_id, key_hash, scopes, expires_at). For MCP external access: generate, revoke, list. `POST /settings/api-keys`.

**Key files created**:
```
python-api/app/
├── services/mcp/
│   ├── tool_generator.py    # Ontology → MCP Tool definitions
│   ├── server.py            # MCP server lifecycle
│   ├── skill_packager.py    # Skill package generation
│   └── auth.py              # MCP auth middleware
├── api/mcp.py               # MCP management endpoints
├── api/skills.py            # Skill listing/download
├── models/
│   ├── mcp_server.py
│   ├── skill.py
│   └── api_key.py
```

**Verify**: Create ontology → `POST /ontology/{id}/mcp/generate` → skill package downloadable → install in Claude Code → `search_orders` tool functional.

---

## Phase 4: Next.js Shell — Auth + Design System + Layout (Day 19-25)

**Goal**: Authentication flow, design tokens applied, main layout with sidebar, core pages as shells

### Tasks

**4.1 Auth system** — NextAuth config with credentials provider + JWT. `Tenant`, `User` Prisma models + migration. Login/Register pages. `PrivateRoute` wrapper. `useSession` hook for all auth state.

**4.2 Design tokens** — `tailwind.config.ts` with custom colors: `bg-root: #fafaf7`, `bg-surface: #f3f2ed`, `bg-data: #f5f4ee`, `accent: #c8842a`, `accent-glow: rgba(200,132,42,0.08)`, `cool: #5b7a8c`, text hierarchy. `globals.css` with CSS variables. Inter font import with `font-feature-settings: 'tnum'`.

**4.3 Base components** — shadcn/ui: Button (amber variant), Card, Input, Select, Dialog, Tabs, DropdownMenu, Tooltip, Separator, Badge, Skeleton.

**4.4 App layout** — `AppLayout` with sticky sidebar (logo, nav items, project selector, user avatar), top header (breadcrumb, notifications). 8px grid spacing. Retro-futurism details: amber hover glow, scan-line skeleton loading.

**4.5 Navigation config** — `navConfig.ts`: navigation items with icons, labels, routes. Sections: Chat (primary), Ontology, Data Sources, Capabilities (能力中心), Settings.

**4.6 Page shells** — Create all route pages as functional shells (no business logic yet):
- `chat/page.tsx` — Chat UI layout with input area
- `ontology/page.tsx`, `ontology/[id]/page.tsx`, `ontology/create/page.tsx`
- `datasources/page.tsx`
- `skills/page.tsx`, `skills/[id]/page.tsx`
- `settings/page.tsx`, `settings/api-keys/page.tsx`

**4.7 Python API client** — `services/pythonApi.ts`: typed HTTP client for all Python endpoints. Base URL from env. Request/response types from TypeScript interfaces matching the Python Pydantic schemas.

**Key files created**:
```
nextjs/src/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── (app)/
│   │   ├── layout.tsx           # AppLayout
│   │   ├── chat/page.tsx
│   │   ├── ontology/
│   │   │   ├── page.tsx
│   │   │   ├── [id]/page.tsx
│   │   │   └── create/page.tsx
│   │   ├── datasources/page.tsx
│   │   ├── skills/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   └── settings/
│   │       ├── page.tsx
│   │       └── api-keys/page.tsx
│   ├── globals.css              # Design tokens
├── components/
│   ├── layout/
│   │   ├── AppLayout.tsx
│   │   ├── Sidebar.tsx
│   │   └── TopNav.tsx
│   ├── shared/
│   │   └── PrivateRoute.tsx
│   └── ui/                      # shadcn primitives
├── services/
│   └── pythonApi.ts             # Typed Python API client
├── types/
│   └── api.ts                   # TypeScript interfaces (QueryRequest, etc.)
├── hooks/
│   └── useAuth.ts
├── lib/
│   ├── auth.ts                  # NextAuth config
│   └── navConfig.ts
└── prisma/
    └── schema.prisma            # User, Tenant, ApiKey, ChatSession
```

**Verify**: Login flow works → redirects to chat → sidebar navigates to all pages → design tokens render correctly. No business logic on pages yet.

---

## Phase 5: Agent Engine + Chat UI (Day 26-35)

**Goal**: Full chat experience — Planning + ReAct agent, streaming UI, OAG result rendering

### Tasks

**5.1 Chat DB model** — Prisma `ChatSession` (tenantId, userId, title, ontologyIds, plan JSON, oagCache JSON, createdAt, updatedAt). `ChatMessage` (sessionId, role, content, toolCalls JSON, planStep, createdAt). Migration.

**5.2 Chat API routes (Next.js)**:
- `POST /api/chat/sessions` — create session
- `GET /api/chat/sessions` — list user's sessions
- `GET /api/chat/sessions/{id}` — session with messages
- `POST /api/chat/sessions/{id}/send` — **core endpoint**: accept message → Planner → ReAct execution → SSE stream back

**5.3 Planner agent** — `app/agent/planner.ts`: given user question + loaded ontology context, LLM generates step plan. Each step has: `description` (Chinese, business language), `tool_hint` (which tool type), `ontology_object` (target object). Return `Plan { steps[], reasoning }`.

**5.4 Tool registry** — `app/agent/tool-registry.ts`: loads tools from Python MCP endpoint for active ontology. Maps tool names to Python API calls. Registry is passed to ReAct agent.

**5.5 ReAct agent** — `app/agent/react.ts`: standard ReAct loop using Vercel AI SDK `streamText` + tool calling. For each step in the plan:
1. LLM thinks → selects tool from registry
2. Execute tool (calls Python API)
3. Observe OAG response → inject into context
4. Continue to next step or finish

**5.6 Streaming chat endpoint** — `POST /api/chat/sessions/{id}/send`:
- Accept `{ message }`, optional `{ auto_approve_plan: boolean }`
- If no plan: Planner generates plan → stream plan to client → wait for user confirmation
- Execute ReAct loop → stream each step's status + results via SSE
- Return final answer with suggested follow-ups

**5.7 Chat UI components**:
- `ChatInput` — input box with ontology context selector, send button
- `PlanCard` — collapsible plan card showing business-language steps, status icons (✅🔄⏳), click to expand technical details
- `StepRunner` — live step status with scan-line animation, tool name + params in collapsible detail
- `ResultView` — OAG result renderer: table (tabular-nums), object card, chart placeholder
- `SuggestionBar` — "建议追加：..." with accept/skip buttons
- `QuestionSidebar` — left sidebar listing all questions in this session, click to jump back

**5.8 Chat session management** — Update session title (auto from first message). Save/restore oag_cache for context continuity. Delete session.

**Key files created**:
```
nextjs/src/
├── app/
│   ├── api/chat/
│   │   ├── sessions/
│   │   │   ├── route.ts          # GET (list), POST (create)
│   │   │   └── [id]/
│   │   │       ├── route.ts      # GET session
│   │   │       └── send/route.ts # POST message + SSE stream
│   ├── agent/
│   │   ├── planner.ts            # Planning agent
│   │   ├── react.ts              # ReAct execution loop
│   │   ├── tool-registry.ts      # Tool loading from Python MCP
│   │   └── oag-context.ts        # OAG cache management
├── components/chat/
│   ├── ChatInput.tsx
│   ├── PlanCard.tsx
│   ├── StepRunner.tsx
│   ├── ResultView.tsx
│   ├── OagTable.tsx
│   ├── ObjectCard.tsx
│   ├── SuggestionBar.tsx
│   └── QuestionSidebar.tsx
├── hooks/
│   └── useAgentSession.ts        # SSE stream + state management
```

**Verify**: Type "华南区毛利为什么下降了？" → Plan appears ("1. 查华南收入/成本变化 2. 找毛利异常品类...") → confirm → ReAct steps execute one by one → final answer with table + chart → suggested follow-ups.

---

## Phase 6: Integration — End-to-end Flows (Day 36-41)

**Goal**: Wire all pages full-stack, implement ontology management UI, datasource UI, skills UI

### Tasks

**6.1 Datasource management** — CRUD data sources. Connection form (MySQL/PG/SQLite/CSV). List with status badges. Dataset detail: sync status, last_synced_at, row count. Manual sync trigger.

**6.2 Ontology creation wizard** — Upload CSV / connect DB → Ingest → schema preview → LLM review suggestions → user confirms → ontology created. Multi-step wizard with progress indicator.

**6.3 Ontology detail page** — Object list with properties/semantic types. Link graph visualization. Function list with descriptions. YAML export button. MCP Server status + start/stop toggle.

**6.4 Capabilities center** — List installable skills with name, description, examples. Download button. Install count.

**6.5 API Key management** — Generate/revoke/list. Scopes display. Copy-to-clipboard.

**6.6 Settings page** — Account info, plan display, basic preferences.

**6.7 E2E test** — Register → create datasource → ingest → ontology created → chat about it → download skill → install in Claude Code → external query works.

**Verify**: Full flow from account creation to external MCP query. All UI states handled (loading, empty, error).

---

## Phase 7: Deployment (Day 42-45)

**Goal**: Docker Compose for local, Railway for SaaS, production hardening

### Tasks

**7.1 Production Docker images** — `Dockerfile.python-api` (multi-stage). `Dockerfile.nextjs` (standalone mode). Non-root user, health checks.

**7.2 Docker Compose production** — `docker-compose.prod.yml` with volume mounts. Env template (`LLM_PROVIDER`, `LLM_API_KEY`). `docker compose up -d` one-command start.

**7.3 Railway deployment** — `railway.json` config. Python API + Next.js as separate services. PostgreSQL plugin. S3 for Delta files.

**7.4 LLM provider abstraction** — Configurable `LLM_PROVIDER` env. Support `openai`, `anthropic`, `ollama`, `vllm`. Abstract adapter per provider.

**7.5 Production hardening** — Rate limiting, CORS, structured JSON logging, graceful shutdown, custom error pages.

**7.6 On-premise package** — Zip: `docker-compose.prod.yml` + `.env.template` + `README.md` (Chinese). Test on clean Ubuntu.

**Verify**: `docker compose -f docker-compose.prod.yml up -d` on clean Ubuntu → all services start → login, ingest, chat, MCP generation all work.

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| delta-rs + DuckDB combo unstable for Chinese data | Blocker | Test with GBK/UTF-8 CSV, Chinese column names early in Phase 1 |
| Vercel AI SDK SSE streaming broke over Docker network | High | Test streaming early in Phase 4; fallback to polling if needed |
| MCP Python SDK breaking changes | Medium | Pin version; wrap in abstraction layer |
| Ontology inference quality poor for arbitrary CSV | Medium | LLM review as gate; MVP accepts manual field mapping |
| Team capacity overrun | High | Cut non-core: simplify graph viz, skip notifications, skip audit log |

---

## Summary

| Phase | Days | What |
|---|---|---|
| 0 | 1-2 | Scaffold |
| 1 | 3-7 | Ingestion + Delta Lake |
| 2 | 8-14 | Ontology Engine + OAG |
| 3 | 15-18 | MCP Server Factory |
| 4 | 19-25 | Auth + Design + Shell |
| 5 | 26-35 | Agent + Chat UI |
| 6 | 36-41 | Integration |
| 7 | 42-45 | Deployment |
| **Total** | **45 days** | **MVP delivered** |

45-day timeline assumes 2 experienced full-stack developers. With 5 people, Phase 4+5 (Next.js) and Phase 1-3 (Python) can overlap significantly, compressing to ~30 days.