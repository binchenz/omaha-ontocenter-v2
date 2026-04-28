# Omaha OntoCenter

Configuration-driven financial analysis platform with ontology management and object exploration for A-share markets.

## Repository Layout

```
omaha_ontocenter/
├── backend/           # FastAPI application (Python)
├── frontend/          # React + TypeScript + Vite UI
├── configs/           # YAML ontology configurations
├── deployment/        # Server deployment scripts
├── docs/              # Operational documentation
├── LOCAL_SETUP.md     # Local dev startup guide
├── RUNNING.md         # How to run and access the app
└── CLAUDE.md          # AI assistant instructions
```

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- **Frontend**: React 18 + TypeScript + Ant Design + Vite
- **Data**: Tushare Pro API, PostgreSQL, MySQL
- **Auth**: JWT-based authentication
- **AI**: DeepSeek / OpenAI / Anthropic (configurable LLM provider)

## Key Features

- **Ontology Management**: YAML-based business object definitions with semantic types
- **Link Type System**: Palantir Foundry-inspired object relationships (forward/reverse navigation, multi-hop paths)
- **Per-Object Tools**: Dynamic tool generation (`search_*`, `count_*`, `aggregate_*`) per ontology object
- **Multi-Datasource**: Cross-datasource queries (PostgreSQL, MySQL, SQLite, Excel, Tushare)
- **AI Agent**: ReAct loop with DeepSeek thinking mode support
- **Auto-Slug Generation**: ASCII-safe identifiers (with pinyin transliteration for Chinese names)

## Active API Surfaces

### Service status
- `GET /` — service metadata and running status
- `GET /health` — health check

### Public auth (`/api/public/auth/*`)
- `POST /api/public/auth/register` — register a user with an invite code
- `POST /api/public/auth/api-key` — generate a public API key

### Public data (`/api/public/v1/*`)
- `GET /api/public/v1/objects` — list available object types
- `GET /api/public/v1/schema/{object_type}` — fetch object schema
- `POST /api/public/v1/query` — run public data queries
- `POST /api/public/v1/aggregate` — run aggregate queries
- `GET /api/public/v1/watchlist` — list public API watchlist items
- `POST /api/public/v1/watchlist` — add a public API watchlist item
- `DELETE /api/public/v1/watchlist/{item_id}` — remove a public API watchlist item

### Authenticated API (`/api/v1/*`)
- `POST /api/v1/auth/login` and `POST /api/v1/auth/register` — authentication
- `GET/POST /api/v1/projects` plus project-specific detail/update/delete routes — project management
- `GET /api/v1/datahub/search` and dataset schema/property routes under `/api/v1/datahub/datasets/*` — DataHub metadata access
- `POST /api/v1/ontology/validate` and `POST /api/v1/ontology/build` — ontology validation and build
- `GET /api/v1/query/{project_id}/objects`, `GET /api/v1/query/{project_id}/schema/{object_type}`, `GET /api/v1/query/{project_id}/relationships/{object_type}`, `POST /api/v1/query/{project_id}/query`, `GET /api/v1/query/{project_id}/history` — object querying
- `POST /api/v1/assets/{project_id}/assets`, `GET /api/v1/assets/{project_id}/assets`, `GET /api/v1/assets/{project_id}/assets/{asset_id}`, `DELETE /api/v1/assets/{project_id}/assets/{asset_id}`, `GET /api/v1/assets/{project_id}/assets/{asset_id}/lineage` — asset management
- `POST /api/v1/chat/{project_id}/sessions`, `GET /api/v1/chat/{project_id}/sessions`, `POST /api/v1/chat/{project_id}/sessions/{session_id}/message`, `DELETE /api/v1/chat/{project_id}/sessions/{session_id}` — chat sessions
- `GET /api/v1/watchlist/`, `POST /api/v1/watchlist/`, `PATCH /api/v1/watchlist/{item_id}`, `DELETE /api/v1/watchlist/{item_id}` — watchlist management

## Quick Start

See [LOCAL_SETUP.md](LOCAL_SETUP.md) for local development setup.

For production deployment, see [deployment/README.md](deployment/README.md).

## Configuration

Ontology configs live in `configs/`. The primary config is `configs/financial_stock_analysis.yaml`.

Environment variables (set in `backend/.env`):
- `DATABASE_URL` — database connection string
- `SECRET_KEY` — JWT signing key
- `TUSHARE_TOKEN` — Tushare Pro API token
- `DATAHUB_GMS_URL` / `DATAHUB_GMS_TOKEN` — optional DataHub integration
