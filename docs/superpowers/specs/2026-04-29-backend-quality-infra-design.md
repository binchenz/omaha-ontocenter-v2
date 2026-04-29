# Backend Quality & Infrastructure Optimization

Date: 2026-04-29
Status: Approved
Scope: Backend code quality + engineering infrastructure
Deployment: Single-server (69.5.23.70), no containerization planned

## Overview

Four-phase optimization plan: error handling → observability → performance → CI/CD. Each phase is independently deployable.

## Phase 1 — Error Handling & Transaction Safety

### 1.1 Eliminate Bare Exceptions

Replace all bare `except:` and overly broad `except Exception:` with specific exception types + logging.

Files to modify:
- `app/services/legacy/financial/ontology_cache_service.py` (lines 64, 101) — bare `except:`
- `app/services/ontology/inferrer.py` (lines 105, 137) — `except Exception:` with silent failure
- `app/services/agent/_legacy_chat_service.py` (lines 187, 204, 954) — broad catches
- `app/services/platform/scheduler.py` (lines 31, 64, 82, 109, 116) — broad catches in background jobs

Rules:
- Replace with specific types: `ValueError`, `ConnectionError`, `SQLAlchemyError`, `KeyError`, etc.
- Every catch block must call `logger.exception()` or `logger.warning()` with context
- Scheduler may keep `except Exception` as last resort, but must log with full traceback
- No silent `pass` in any catch block

### 1.2 Database Transaction Protection

Add try/except + rollback to all write-path endpoints. Keep explicit `db.commit()` pattern (do NOT move to auto-commit in `get_db()`).

Pattern:
```python
try:
    db.add(obj)
    db.commit()
    db.refresh(obj)
except SQLAlchemyError:
    db.rollback()
    logger.exception("Failed to create %s", obj.__class__.__name__)
    raise HTTPException(status_code=500, detail="Database operation failed")
```

Scope: All endpoints in `app/api/` that call `db.commit()`. Estimated ~20 locations.

### 1.3 Fix SQL Injection in slug.py

`app/services/ontology/slug.py:64` — `table_name` and `column_name` are interpolated directly into SQL.

Fix: Add allowlist validation before any dynamic SQL:
```python
import re
def _validate_identifier(name: str) -> str:
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name
```

Also audit `app/mcp/tools.py` for similar risks in filter/join parameters.

### 1.4 Unified API Error Response

Current state: Mix of `status.HTTP_404_NOT_FOUND` vs raw `404`, inconsistent response shapes.

Changes:
- Define `ErrorResponse` schema: `{"error": str, "detail": str | None, "request_id": str}`
- Add global exception handler in `app/main.py` for unhandled exceptions
- Standardize all `HTTPException` calls to use `status.*` constants
- Return consistent error shape from all endpoints

## Phase 2 — Structured Logging & Health Checks

### 2.1 Structured Logging with structlog

Add `structlog` dependency. Configure JSON output for production, colored console for dev.

Setup in `app/main.py`:
- Initialize structlog with processors: add_log_level, timestamp (ISO), JSONRenderer
- Add FastAPI middleware to inject `request_id` (UUID4), `user_id`, `method`, `path` into log context
- Replace all existing `logging.getLogger()` calls with `structlog.get_logger()`

Log points:
- `INFO`: Request start/end, query execution, ontology operations, MCP tool calls
- `WARNING`: Auth failures, missing config, degraded service
- `ERROR`: Exception catches, external API failures, transaction rollbacks

Note: Phase 1 introduces `logger` calls using stdlib `logging`. Phase 2 migrates these to `structlog`. This is intentional — Phase 1 focuses on correctness, Phase 2 on observability.

File output: `/var/log/omaha/app.log` with logrotate (daily, 30 days retention).

### 2.2 Enhanced Health Check

Replace trivial `/health` endpoint with:
```json
{
    "status": "healthy | degraded | unhealthy",
    "checks": {
        "database": "ok | error",
        "tushare_configured": true,
        "llm_configured": true
    },
    "version": "read from app/config.py Settings.APP_VERSION",
    "uptime_seconds": 3600
}
```

- Database: execute `SELECT 1` with 2s timeout
- External services: check config presence only (no live connectivity test)
- Return 200 for healthy/degraded, 503 for unhealthy

### 2.3 Audit Logging

Use existing `AuditLog` model. Add writes at:
- Login success/failure
- Ontology create/update/delete
- Data query execution (object, filters, user)
- API key creation/revocation
- Project membership changes

## Phase 3 — Performance Optimization

### 3.1 Ontology Config Caching

`services/legacy/financial/omaha.py` parses YAML on every request.

Fix: Add file-mtime-based cache. Check `os.path.getmtime()` on each access; re-parse only if changed. Use a module-level dict as cache store. No external cache dependency needed.

### 3.2 N+1 Query Fixes

Affected endpoints:
- `api/projects/crud.py` — project listing loads members lazily
- `api/chat/chat.py` — session listing loads messages lazily

Fix: Add `joinedload()` or `selectinload()` to queries that return lists with relationships.

### 3.3 HTTP Caching

Add `Cache-Control` and `ETag` headers to read-only endpoints:
- `GET /api/v1/ontology/objects` — cache 60s
- `GET /api/v1/ontology/objects/{id}/schema` — cache 60s
- `GET /api/v1/query/datasources` — cache 300s

Use middleware or per-endpoint response headers.

## Phase 4 — CI/CD Pipeline

### 4.1 GitHub Actions Workflow

Trigger: push to main, pull requests.

Steps:
1. `ruff check backend/` — linting
2. `ruff format --check backend/` — formatting
3. `mypy backend/app/ --ignore-missing-imports` — type checking (start permissive, tighten over time)
4. `cd backend && pytest` — tests
5. (main only) SSH deploy: `git pull → pip install -r requirements.txt → alembic upgrade head → systemctl restart omaha-cloud`

### 4.2 Pre-commit Hooks

Add `.pre-commit-config.yaml`:
- ruff (lint + format)
- check-yaml
- check-merge-conflict
- no-commit-to-branch (protect main)

### 4.3 Deploy Safety

- Deploy script checks `pytest` exit code before restarting service
- Post-deploy health check: curl `/health` and verify 200
- If health check fails, rollback to previous commit

## Out of Scope

- Frontend changes (separate initiative)
- Security credential rotation (should be done manually, immediately)
- Database migration to PostgreSQL
- Containerization / Kubernetes
- External monitoring services (Sentry, Datadog)

## Success Criteria

- Zero bare `except:` or silent exception handlers in codebase
- All write endpoints have transaction rollback protection
- Structured JSON logs with request_id on every request
- Health check reports actual database connectivity
- Ontology config parsed at most once per file change
- CI pipeline runs on every push, blocks merge on failure
