# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Omaha OntoCenter v2 is a configuration-driven financial analysis platform with ontology management and object exploration capabilities. The system uses YAML-based ontology configurations to define business objects (stocks, financial indicators, etc.) and supports multi-datasource querying.

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy + PostgreSQL/SQLite
- Frontend: React 18 + TypeScript + Vite + Ant Design
- Data Sources: Tushare Pro API, PostgreSQL, MySQL
- Core Services: OmahaService (query execution), SemanticService (type formatting), ComputedPropertyEngine

## Development Commands

### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Initialize database (SQLite for local dev)
python init_db.py

# Run database migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Start development server (with hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the startup script
./start_backend.sh

# Run tests
pytest

# Run specific test file
pytest tests/test_api_chat.py

# Run tests with coverage
pytest --cov=app tests/
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm preview

# Lint code
npm run lint
```

### Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and start
docker-compose up -d --build
```

## Architecture

### Backend Structure

```
backend/
├── app/                         # FastAPI application
│   ├── api/                    # API endpoints — domain-grouped
│   │   ├── auth/               # Authentication routes (login, api_keys, public_auth)
│   │   ├── chat/               # Chat session and agent routes
│   │   ├── ontology/           # Ontology validation/build/store/semantic routes
│   │   ├── pipelines/          # Pipeline management routes
│   │   ├── projects/           # Project CRUD/members/assets/audit routes
│   │   ├── legacy/financial/   # Legacy financial query/datasources/datahub/watchlist
│   │   ├── deps.py             # Shared FastAPI dependencies
│   │   └── public_deps.py      # Public-API key dependencies
│   ├── models/                 # SQLAlchemy ORM — domain-grouped, __init__ re-exports all
│   │   ├── auth/               # User, Tenant, ApiKey, InviteCode
│   │   ├── chat/               # ChatSession, ChatMessage, QueryHistory, PublicQueryLog
│   │   ├── ontology/           # OntologyObject, ObjectProperty, DatasetAsset, DataLineage
│   │   ├── pipeline/           # Pipeline, PipelineRun
│   │   ├── project/            # Project, ProjectMember, AuditLog
│   │   └── legacy/financial/   # CachedStock, CachedFinancial, Watchlist
│   ├── schemas/                # Pydantic schemas — domain-grouped
│   │   ├── auth/               # User/Token/Login schemas
│   │   ├── chat/               # Chat, agent, structured response schemas
│   │   ├── ontology/           # Ontology, ontology_store, auto_model schemas
│   │   ├── project/            # Project, asset schemas
│   │   └── legacy/financial/   # Public query, watchlist schemas
│   ├── services/               # Business logic — domain-grouped
│   │   ├── agent/              # ReAct agent, toolkit, chat_service, chart_engine
│   │   ├── data/               # Data cleaner, uploaded table store
│   │   ├── ontology/           # Store, importer, inferrer, draft_store, template_loader, schema_scanner
│   │   ├── platform/           # Scheduler, pipeline_runner, audit, datahub
│   │   ├── semantic/           # Service, validator, formatter, computed_property
│   │   └── legacy/financial/   # OmahaService, query_builder, ontology_cache_service
│   ├── connectors/             # External data-source connectors (csv, mongodb, rest, sql, tushare)
│   ├── core/                   # Security utilities (JWT, password hashing)
│   ├── mcp/                    # Model Context Protocol server
│   ├── config.py               # Application settings
│   ├── database.py             # Database connection
│   └── main.py                 # FastAPI app entry point
├── alembic/                    # Database migrations
└── tests/
    ├── unit/{ontology,data,agent,semantic,platform}/  # Unit tests mirror services/
    ├── api/                    # API endpoint tests
    └── integration/            # Cross-service integration tests
```

**Key API Routes:**
- `/api/v1/auth` - User authentication (login, register)
- `/api/v1/projects` - Project CRUD operations
- `/api/v1/datahub` - DataHub metadata integration
- `/api/v1/ontology` - Ontology configuration management
- `/api/v1/query` - Object querying and exploration
- `/api/v1/assets` - Asset management
- `/api/v1/chat` - Chat interface with LLM integration

### Frontend Structure

```
frontend/src/
├── pages/                # Page components — domain-grouped
│   ├── assistant/        # AssistantPage (v2 main chat UI)
│   ├── ontology/         # ModelingPage, OntologyBrowser, OntologyGraph
│   ├── dashboard/        # DashboardPage
│   ├── apps/             # AppsPage, DatasourcePage, PipelinesPage
│   ├── settings/         # SettingsPage, ApiKeysPage, AuditPage
│   ├── legacy/           # v1 pages (ObjectExplorer, OntologyMap, QueryBuilder, etc.)
│   └── (root)            # Login, Register, ProjectList, Settings, ChatAgent, ChatPage
├── components/
│   ├── chat/             # Chat UI components
│   ├── layout/           # MainLayout, ProjectSwitcher, Sidebar
│   ├── shared/           # PrivateRoute, RequireProject, ApiKeyManager, QueryChart
│   ├── ui/               # shadcn primitives
│   └── legacy/           # Legacy v1 components (map/, etc.)
├── layouts/              # AppLayout, TopNav, ModuleSidebar, navConfig
├── services/             # API client services (api, auth, project, ontology, query, asset, chatApi)
├── types/                # TypeScript type definitions
├── hooks/                # Custom React hooks
└── contexts/             # React contexts
```

### Core Services

The `app/services/` directory contains the core business logic, grouped by domain:

- **OmahaService** (`legacy/financial/omaha.py`): YAML config parsing, query execution, multi-datasource support
- **SemanticService** (`semantic/service.py`): Semantic type formatting (currency, percentage, date, ratio, etc.)
- **SemanticQueryBuilder** (`legacy/financial/query_builder.py`): Queries with semantic enhancements and default filters
- **ComputedPropertyEngine** (`semantic/computed_property.py`): Evaluates computed properties defined in ontology configs
- **SemanticTypeFormatter** (`semantic/formatter.py`): Formats query results based on semantic types
- **AgentToolkit** (`agent/toolkit.py`): LLM function-calling toolkit
- **ChatService** (`agent/chat_service.py`): Chat session orchestration with LLM integration

### YAML Configuration Structure

Ontology configs (in `configs/`) define business objects with:
- **datasources**: Connection info for Tushare, PostgreSQL, MySQL
- **objects**: Business object definitions with fields, semantic types, computed properties, and default filters
- **Environment variable substitution**: Only uppercase patterns like `${VAR_NAME}` are substituted (lowercase `${var}` will NOT work)

## Database

**Local Development:** Uses SQLite (`backend/omaha.db`)

**Production:** PostgreSQL via Docker Compose

**Migrations:** Managed with Alembic
- Migration files in `backend/alembic/versions/`
- Always run `alembic upgrade head` after pulling new migrations
- Create migrations with `alembic revision --autogenerate -m "description"`

## Authentication

- JWT-based authentication using `python-jose`
- Password hashing with `bcrypt` via `passlib`
- Token expiration configured in `app/config.py`
- Security utilities in `app/core/security.py`

## Configuration

**Backend:** Environment variables in `.env` or `backend/.env`
- `DATABASE_URL` - Database connection string
- `SECRET_KEY` - JWT signing key
- `DATAHUB_GMS_URL` - DataHub GMS endpoint (optional)
- `DATAHUB_GMS_TOKEN` - DataHub authentication token (optional)
- `TUSHARE_TOKEN` - Tushare Pro API token (for financial data)

**Ontology Configs:** YAML files in `configs/` directory
- Example: `configs/legacy/financial/financial_stock_analysis.yaml`
- Industry templates: `configs/templates/*.yaml` (e.g. retail.yaml)
- Environment variable substitution: Only uppercase patterns like `${TUSHARE_TOKEN}` are substituted
- Lowercase patterns like `${var}` will NOT be substituted

## Testing

**Backend tests** in `backend/tests/` use pytest with mocking:
- `test_api_*.py` - API endpoint tests
- `test_models_*.py` - Model tests
- `test_schemas_*.py` - Schema validation tests
- `test_*_service.py` - Service layer tests

**Root-level test files** for integration testing:
- `test_phase3_real_scenario.py` - Real-world scenario tests with Tushare data
- `test_tushare.py` - Tushare API integration tests
- `test_default_filters.py` - Default filter behavior tests

Run backend tests from the `backend/` directory. Run integration tests from the project root.

## Local Development Workflow

1. Initialize database: `cd backend && python init_db.py`
2. Start backend: `cd backend && uvicorn app.main:app --reload`
3. Start frontend: `cd frontend && npm run dev`
4. Access frontend at http://localhost:5173 (or http://localhost:3000)
5. Access API docs at http://localhost:8000/docs

See `LOCAL_SETUP.md` and `RUNNING.md` for detailed setup instructions.

## MCP Server

The backend includes a Model Context Protocol (MCP) server implementation in `app/mcp/`:
- **server.py**: MCP server setup and tool registration
- **tools.py**: MCP tool implementations for ontology queries
- **auth.py**: Authentication for MCP connections

Run the MCP server standalone:
```bash
cd backend
python -m app.mcp.server
```

## Recent Features

- Chat API with LLM integration and function calling
- MCP server for Claude Code integration
- Asset management endpoints
- Multi-datasource query execution
- YAML-based ontology configuration with validation
- DataHub metadata integration
