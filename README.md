# Omaha OntoCenter

AI-native data platform for SMEs. Upload your business data, let AI build the ontology, then query it through natural language conversation.

## What It Does

1. **Upload** — CSV, Excel, or connect a database (MySQL, PostgreSQL, SQLite)
2. **Model** — AI infers business objects, fields, and relationships from your data
3. **Query** — Ask questions in natural language; the agent writes and executes queries for you

No SQL knowledge required. No BI tool configuration. Just data and questions.

## Repository Layout

```
omaha_ontocenter/
├── backend/           # FastAPI application (Python)
├── frontend/          # React + TypeScript + Vite UI
├── configs/           # YAML ontology templates
├── deployment/        # Server deployment scripts
├── docs/              # Operational documentation
├── LOCAL_SETUP.md     # Local dev startup guide
└── RUNNING.md         # How to run and access the app
```

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (prod)
- **Frontend**: React 18 + TypeScript + Ant Design + Vite
- **LLM**: DeepSeek / OpenAI / Anthropic (configurable)
- **Connectors**: SQLite, MySQL, PostgreSQL, CSV/Excel
- **Auth**: JWT-based authentication

## Key Capabilities

- **Conversational Modeling** — upload tables, AI infers ontology with data quality warnings
- **Per-Object Tools** — dynamic `search_*`, `count_*`, `aggregate_*` tools generated per business object
- **Link Type System** — object relationships with forward/reverse navigation and multi-hop paths
- **Multi-Datasource** — query across different databases in a single ontology
- **ReAct Agent** — multi-step reasoning with tool use, thinking mode, and context retention
- **MCP Server** — Model Context Protocol integration for external AI tools

## Quick Start

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install && npm run dev
```

Access the app at http://localhost:5173

See [LOCAL_SETUP.md](LOCAL_SETUP.md) for detailed setup. See [RUNNING.md](RUNNING.md) for running instructions.

## Configuration

Environment variables (`.env` at project root):

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Database connection string |
| `SECRET_KEY` | Yes | JWT signing key |
| `DEEPSEEK_API_KEY` | One of three | DeepSeek API key |
| `OPENAI_API_KEY` | One of three | OpenAI API key |
| `ANTHROPIC_API_KEY` | One of three | Anthropic API key |

At least one LLM API key must be configured.

## API Overview

| Endpoint Group | Purpose |
|---------------|---------|
| `POST /api/v1/auth/*` | Authentication (login, register) |
| `/api/v1/projects/*` | Project CRUD, members, audit |
| `/api/v1/ontology-store/*` | Ontology object management |
| `/api/v1/chat/{project_id}/*` | Chat sessions and AI agent |
| `/api/v1/assets/*` | Dataset asset management |
| `GET /health` | Health check |

Full API documentation available at `http://localhost:8000/docs` when running locally.

## Deployment

See [deployment/README.md](deployment/README.md) for production deployment instructions.

## License

Proprietary. All rights reserved.
