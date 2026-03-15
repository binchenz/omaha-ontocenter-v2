# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Omaha OntoCenter v2 is a configuration-driven pricing analysis platform with ontology management and object exploration capabilities. The system integrates with DataHub for metadata discovery and supports multi-datasource querying (PostgreSQL, MySQL).

**Tech Stack:**
- Backend: FastAPI + SQLAlchemy + PostgreSQL/SQLite
- Frontend: React 18 + TypeScript + Vite + Ant Design
- Core: Omaha Core library for configuration and query execution

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
│   ├── models/            # SQLAlchemy ORM models
│   ├── schemas/           # Pydantic schemas for request/response
│   ├── services/          # Business logic layer
│   ├── config.py          # Application settings
│   ├── database.py        # Database connection
│   └── main.py            # FastAPI app entry point
├── omaha/                 # Omaha Core library
│   ├── core/
│   │   ├── config/        # YAML configuration loader with env var substitution
│   │   ├── ontology/      # Ontology management
│   │   ├── data/          # Data access layer
│   │   └── agent/         # LLM orchestration (LangGraph)
│   ├── cli/               # CLI interface
│   └── utils/             # Utilities and exceptions
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

### Omaha Core Library

The `omaha/` directory contains the core business logic:

- **Configuration Layer**: YAML-based ontology configuration with environment variable substitution (pattern: `${VAR_NAME}` for uppercase vars only)
- **Ontology Management**: Schema validation and business object definitions
- **Data Layer**: Multi-datasource query execution with SQLAlchemy
- **Agent Layer**: LLM orchestration using LangGraph for intelligent query assistance

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
- `DATAHUB_GMS_URL` - DataHub GMS endpoint
- `DATAHUB_GMS_TOKEN` - DataHub authentication token

**Omaha Core:** YAML configuration files with environment variable substitution
- Only uppercase patterns like `${VAR_NAME}` are substituted
- Lowercase patterns like `${var}` will NOT be substituted

## Testing

Tests are located in `backend/tests/` and use pytest with mocking:
- `test_api_*.py` - API endpoint tests
- `test_models_*.py` - Model tests
- `test_schemas_*.py` - Schema validation tests
- `test_*_service.py` - Service layer tests

Run tests from the `backend/` directory.

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
