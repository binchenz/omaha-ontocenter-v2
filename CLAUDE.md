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
├── app/                    # FastAPI application
│   ├── api/               # API endpoints (auth, projects, datahub, ontology, query, assets, chat)
│   ├── core/              # Security utilities (JWT, password hashing)
│   ├── mcp/               # Model Context Protocol server implementation
│   ├── models/            # SQLAlchemy ORM models (User, Project, Asset, ChatSession, QueryHistory, APIKey)
│   ├── schemas/           # Pydantic schemas for request/response
│   ├── services/          # Business logic layer
│   │   ├── omaha.py       # Core service: YAML config parsing, query execution, multi-datasource support
│   │   ├── semantic.py    # Semantic type formatting (currency, percentage, date, etc.)
│   │   ├── query_builder.py        # Query builder with semantic enhancements
│   │   ├── computed_property_engine.py  # Computed property evaluation
│   │   └── semantic_formatter.py   # Format output based on semantic types
│   ├── config.py          # Application settings
│   ├── database.py        # Database connection
│   └── main.py            # FastAPI app entry point
├── alembic/               # Database migrations
└── tests/                 # Test suite
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
├── components/            # Reusable UI components
├── pages/                # Page components
│   ├── Login.tsx
│   ├── Register.tsx
│   ├── ProjectList.tsx
│   ├── ProjectDetail.tsx
│   ├── ObjectExplorer.tsx
│   └── AssetList.tsx
├── services/             # API client services
│   ├── api.ts           # Base axios configuration
│   ├── auth.ts          # Authentication API
│   ├── project.ts       # Project API
│   ├── ontology.ts      # Ontology API
│   ├── query.ts         # Query API
│   ├── asset.ts         # Asset API
│   └── chatApi.ts       # Chat API
├── types/               # TypeScript type definitions
├── hooks/               # Custom React hooks
└── utils/               # Utility functions
```

### Core Services

The `app/services/` directory contains the core business logic:

- **OmahaService** (`omaha.py`): Main service for YAML config parsing, query execution, and multi-datasource support (Tushare, PostgreSQL, MySQL, SQLite)
- **SemanticService** (`semantic.py`): Handles semantic type formatting (currency, percentage, date, ratio, etc.)
- **SemanticQueryBuilder** (`query_builder.py`): Builds queries with semantic enhancements and default filters
- **ComputedPropertyEngine** (`computed_property_engine.py`): Evaluates computed properties defined in ontology configs
- **SemanticTypeFormatter** (`semantic_formatter.py`): Formats query results based on semantic types

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
- Example: `configs/financial_stock_analysis.yaml`
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

## Recent Features

- Chat API with LLM integration and function calling
- Asset management endpoints
- Multi-datasource query execution
- YAML-based ontology configuration with validation
- DataHub metadata integration
