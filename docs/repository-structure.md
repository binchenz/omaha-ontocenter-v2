# Repository Structure

## Current Root Files

The repository root currently contains the main entrypoint documents and project-level configuration:

- `README.md` — project overview and active API surfaces
- `LOCAL_SETUP.md` — local development setup
- `RUNNING.md` — run and access instructions
- `CLAUDE.md` — repository-specific assistant guidance
- `.env.example` — environment variable template

Current root entries are limited to entrypoint documents and project-level configuration; generated artifacts, archives, one-off test scripts, and report files are absent.

## Current Top-Level Directories

| Directory | Purpose |
|-----------|---------|
| `backend/` | FastAPI application, MCP server, migrations, and backend tests |
| `frontend/` | React + TypeScript web application |
| `configs/` | Active ontology and environment-backed config files |
| `deployment/` | Deployment and maintenance scripts |
| `docs/` | Project documentation and references |
| `.claude/` | Claude Code project configuration |
