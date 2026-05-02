# OntoCenter

AI-native data platform for Chinese SMEs. Upload business data, let AI build the ontology, then query it through natural language.

**Source lives in [`v3/`](./v3).** See [v3/README.md](./v3/README.md) for setup, architecture, and commands.

```
omaha_ontocenter/
├── v3/                 # The application
│   ├── python-api/     # FastAPI + Delta Lake + DuckDB — data layer
│   ├── nextjs/         # Next.js 14 + Vercel AI SDK — chat + MCP server + UI
│   ├── docker-compose.yml
│   └── README.md       # ← start here
└── docs/superpowers/   # Design specs + implementation plans
```

## Quick start

```bash
cd v3
docker compose up -d            # postgres + python-api + nextjs
open http://localhost:3000      # demo@ontocenter.dev / demo123
```

Or local dev (no Docker): follow [v3/README.md](./v3/README.md#快速开始).

## What it does

1. Upload CSV/Excel or connect MySQL/PostgreSQL → AI infers schema and semantic types
2. Ask questions in Chinese or English → Agent routes to the right tool, queries, summarizes
3. Generate API key → connect the assistant Desktop / Cursor / any MCP client via the built-in MCP server

## Status

Actively developed. v1 (`backend/` + `frontend/`) was removed in favor of v3. In-flight work and design specs live in [docs/superpowers/plans/](./docs/superpowers/plans/).
