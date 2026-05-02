# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Omaha OntoCenter v3 — AI-native data analysis platform for Chinese SMEs ("Palantir for Chinese SMEs"). Users upload business data, AI builds the ontology, then they query it through natural language chat.

**Tech Stack:**
- **Next.js 14** — Chat UI + LLM Agent (Vercel AI SDK) + MCP server (JSON-RPC) + BFF
- **Python FastAPI** — Pure data layer: ingest / ontology CRUD / OAG query / datasources
- **Delta Lake + DuckDB** — Data versioning + columnar query
- **PostgreSQL** (prod) / **SQLite** (dev) — Chat sessions + users + API keys (via Prisma)
- **LLM** — DeepSeek / OpenAI / Anthropic (configurable)

All source lives in `v3/`. The root directory contains only `v3/`, `docs/superpowers/`, `CLAUDE.md`, and `README.md`.

## Development Commands

### Python API (data layer)

```bash
cd v3/python-api
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
# Tests: pytest (40 tests)
```

### Next.js (agent + UI + MCP)

```bash
cd v3/nextjs
npm install
npx prisma generate && npx prisma db push
NO_PROXY=localhost,127.0.0.1 npm run dev
# Type check: npx tsc --noEmit
```

### Docker

```bash
cd v3
docker compose up -d
# Frontend: http://localhost:3000 (demo@ontocenter.dev / demo123)
# Backend API docs: http://localhost:8000/docs
```

## Architecture

```
User (boss) → Next.js BFF → LLM (Skill router + ReAct) → Python API → DuckDB + Delta Lake
                             ↓
Claude Desktop / Cursor → /api/mcp (JSON-RPC, Bearer auth) ─┘
                             ↓
                       tool-registry.ts (single source of truth)
```

After A1 unification: MCP server runs in Next.js. Python is a pure data layer (no LLM, no MCP, no tool generation).

### Next.js Structure

```
v3/nextjs/src/
├── app/agent/           # LLM agent core
│   ├── tool-registry.ts # Single source of truth: search_*/aggregate_*/count_* + ingest tools
│   ├── react.ts         # Vercel AI SDK streamText wrapper
│   ├── skill-router.ts  # Heuristic-first routing → LLM fallback
│   ├── skill-loader.ts  # SKILL.md parser (gray-matter)
│   ├── skills.ts        # Skill name constants
│   ├── mcp-adapter.ts   # Tool→MCP JSON Schema converter
│   └── llm.ts           # LLM model config (OpenAI-compatible)
├── app/api/
│   ├── chat/sessions/   # Chat CRUD + /send (main agent endpoint)
│   ├── mcp/route.ts     # JSON-RPC: initialize, tools/list, tools/call (Bearer auth)
│   ├── keys/            # API key management
│   ├── proxy/python/    # Client-side → Python proxy (adds internal auth)
│   └── python/ingest/   # File upload proxy
├── app/(app)/           # Pages: chat, datasources, ontology, settings, skills
├── app/(auth)/          # Login page
├── components/          # Chat UI, layout (AppLayout, Sidebar, Providers)
├── lib/
│   ├── session.ts       # SessionContext, ownedSessionWhere(), ensureDemoIdentity()
│   ├── bearerAuth.ts    # API key auth (SHA-256 hash lookup)
│   ├── internalAuth.ts  # X-Internal-Auth header injection
│   ├── constants.ts     # UPLOAD_MARKER, UPLOAD_MARKER_RE
│   └── prisma.ts        # Prisma client singleton
├── services/
│   └── pythonApi.ts     # Dual-context: server→direct, client→/api/proxy/python
├── skills/              # SKILL.md files (data-ingest, data-query, data-explore, general-chat)
└── types/               # API types, NextAuth extensions
```

### Python API Structure

```
v3/python-api/app/
├── api/                 # FastAPI endpoints (pure data, no LLM)
│   ├── ingest.py        # File upload + Delta Lake write
│   ├── ontology.py      # Ontology CRUD + OAG query
│   ├── datasources.py   # Datasource management
│   ├── health.py        # Health check (bypasses auth)
│   └── deps.py          # TenantId, Pagination dependencies
├── models/              # SQLAlchemy ORM (ontology, datasource)
├── schemas/             # Pydantic schemas (ingest, ontology_config, query)
├── services/
│   ├── ingest/          # Coordinator, delta_writer, schema_inferrer
│   ├── ontology/        # Store, parser, slug, dto (build_oag_context)
│   └── query/           # duckdb_service, oag_service, view_registry, sql_safety, function_engine
├── connectors/          # CSV/SQLite/MySQL/PostgreSQL connectors
├── core/                # Crypto, locks
├── functions/           # Custom stat functions
├── config.py            # Settings (env_file pinned to python-api/)
├── database.py          # Async SQLAlchemy engine
└── main.py              # FastAPI app + internal_auth middleware
```

## Key Concepts

### Skill System
Skills are SKILL.md files with YAML frontmatter (name, description, triggers) + markdown body for LLM instructions. Four skills: `data-ingest`, `data-query`, `data-explore`, `general-chat`. Routing is heuristic-first (keyword matching ~80%) with LLM `generateObject` fallback.

### Tool Registry
`tool-registry.ts` is the single source of truth. Per-ontology tools (`search_<slug>_<ontology>`, `aggregate_*`, `count_*`) are generated from schema. Ingest tools (`list_my_data`, `create_ontology`) are added conditionally. MCP and chat share the same tool set via `loadTenantToolSet()`.

### Auth
- **Cookie-based** (NextAuth): for browser sessions → `getSessionContext()`
- **Bearer API key**: for MCP clients → `getBearerContext()` (SHA-256 hashed, `@unique` index)
- **Internal shared-secret**: Python↔Next.js via `X-Internal-Auth` header; `/health` bypassed

### Data Flow
1. Upload CSV → Python ingest → Delta Lake (schema_mode="overwrite")
2. Create ontology → Python store → SQLAlchemy ORM
3. Query → DuckDB view (tenant-scoped via SHA-1 `safe_view_name`) → JSON response
4. Chat → skill router → tool selection → Python API → DuckDB → LLM summarizes

### Slug System
Ontology objects/properties have ASCII `slug` alongside Chinese `name`. Generated via `slugify_name()` with pypinyin transliteration. Required because LLM tool names must match `^[a-zA-Z0-9_-]+$`.

## Configuration

### Next.js (`v3/nextjs/.env.local`)
- `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `LLM_MODEL` — LLM provider config
- `PYTHON_API_URL` — Python API URL (default: http://127.0.0.1:8000)
- `INTERNAL_API_SECRET` — Shared secret for Python↔Next.js auth
- `NEXTAUTH_SECRET` / `NEXTAUTH_URL` — NextAuth config
- `DATABASE_URL` — Prisma database URL

### Python API (`v3/python-api/.env`)
- `DATABASE_URL` — SQLAlchemy async database URL
- `INTERNAL_API_SECRET` — Must match Next.js value
- `DATA_DIR` — Delta Lake storage path

## Testing

```bash
# Python API tests (40 tests)
cd v3/python-api && source .venv/bin/activate && pytest

# Next.js type check
cd v3/nextjs && npx tsc --noEmit
```

## Deployment

```bash
# Docker Compose (local)
cd v3 && docker compose up -d

# Railway (SaaS)
railway up
```
