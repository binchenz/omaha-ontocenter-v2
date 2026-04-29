# Product Repositioning: Remove Financial Vertical, Pure SME Platform

Date: 2026-04-30
Status: Approved
Decision: Remove all financial-specific code; retain and promote the generic query engine.

## Context

Omaha OntoCenter was originally prototyped using financial/stock data (Tushare API) as a verification domain. The project's true positioning is a **generic SME ontology data platform**. Financial code now creates naming confusion (`legacy/financial/` is actually live infrastructure), bloats the codebase, and misleads contributors about the product direction.

## Decision

**Delete all financial-specific code.** Retain the generic query engine capabilities (YAML config parsing, multi-datasource query, semantic formatting, filter/join/aggregate) and promote them from `app/services/legacy/financial/` to `app/services/query/`.

## What Gets Deleted

### API Routes (5 files, ~818 lines)
- `app/api/legacy/financial/query.py` — stock query endpoint
- `app/api/legacy/financial/datasources.py` — datasource CRUD (financial-specific)
- `app/api/legacy/financial/datahub.py` — DataHub integration
- `app/api/legacy/financial/watchlist.py` — stock watchlist
- `app/api/legacy/financial/public_query.py` — public API for financial queries
- `app/api/legacy/financial/__init__.py`
- Router registrations in `app/api/__init__.py` and `app/main.py`

### Models (5 files, ~147 lines)
- `app/models/legacy/financial/cached_stock.py` — CachedStock
- `app/models/legacy/financial/cached_financial.py` — CachedFinancialIndicator
- `app/models/legacy/financial/cached_financial_statements.py` — Income/Balance/CashFlow
- `app/models/legacy/financial/watchlist.py` — Watchlist
- `app/models/legacy/financial/__init__.py`
- Remove `User.watchlist` relationship in `app/models/auth/user.py`
- Re-export cleanup in `app/models/__init__.py`

### Schemas (3 files, ~135 lines)
- `app/schemas/legacy/financial/public_query.py`
- `app/schemas/legacy/financial/watchlist.py`
- `app/schemas/legacy/financial/__init__.py`

### Services (2 files, ~640 lines deleted)
- `app/services/legacy/financial/ontology_cache_service.py` — entire file (only served public_query)
- `app/services/legacy/financial/omaha.py` — DELETE financial-specific methods:
  - `_query_tushare()` (~110 lines)
  - `_compute_technical_indicators()` (~96 lines)
  - `analyze_pricing()` (~30 lines)
  - Tushare imports and env-var substitution for TUSHARE_TOKEN

### Connectors (1 file, ~80 lines)
- `app/connectors/tushare_connector.py` — entire file
- Remove `tushare` registration from `app/connectors/__init__.py`

### Configs (1 file, 786 lines)
- `configs/legacy/financial/financial_stock_analysis.yaml`
- Remove `configs/legacy/` directory entirely
- Remove `LEGACY_FINANCIAL_CONFIG` from `app/_paths.py`

### Agent (partial cleanup)
- `app/services/agent/_legacy_chat_service.py` — 1,083 lines, entire file (Wave 3 cleanup — no external consumers after Wave 2)
- Remove `screen_stocks` tool from MCP `app/mcp/tools.py` and `app/mcp/server.py`
- Remove `screen_stocks` from `app/services/agent/skills/definitions/data_query.yaml`
- Remove `ChatService` re-export from `app/services/agent/chat_service.py`

### Config/Settings cleanup
- `app/config.py`: remove `TUSHARE_TOKEN`, `DATAHUB_GMS_URL`, `DATAHUB_GMS_TOKEN`
- `app/main.py` health check: remove `tushare_configured` check
- `.env.example`: remove Tushare and DataHub entries

### DataHub cleanup
- `app/services/platform/datahub.py` — delete entire DataHub integration service
- `app/api/legacy/financial/datahub.py` — already deleted with the API routes above
- `app/models/project/project.py` — remove `datahub_dataset_urn` column
- `app/schemas/project/project.py` — remove `datahub_dataset_urn` field

### Frontend
- Delete `frontend/src/pages/legacy/Explorer.tsx` (11 lines, stock explorer wrapper)
- Delete `frontend/src/pages/legacy/QueryHistory.tsx` (88 lines, financial query history)
- Remove associated routes from `App.tsx` (`/explorer`, `/history`)
- Other `pages/legacy/*.tsx` files (DatasourceManager, OntologyEditor, etc.) are generic business components imported by v2 pages — **keep and rename to `pages/shared/`**

### Tests
- Delete all test files that test financial-specific functionality
- Update tests that import `OmahaService` from `legacy/financial/` path

### Database Migration
- Alembic migration to drop: `cached_stocks`, `cached_financial_indicators`, `cached_income_statements`, `cached_balance_sheets`, `cached_cash_flows`, `watchlist` tables
- Drop `datahub_dataset_urn` column from `projects`

## What Gets Retained and Moved

### Query Engine: `app/services/legacy/financial/omaha.py` → `app/services/query/engine.py`

Retained capabilities (the generic query engine):
- `parse_config()` — YAML config parsing
- `_parse_ontology()` — ontology extraction from YAML
- `build_ontology()` — object/relationship building
- `get_relationships()` — relationship discovery
- `get_object_schema()` — schema introspection
- `query_objects()` — the core query method (filter/select/limit/join)
- `_query_connector()` — delegation to SQLite/MySQL connectors
- `_build_where_clause()` — filter building
- `_build_select_query()` — SQL generation
- `_build_join_clause()` — join building
- `_connect_sqlite()` / `_connect_mysql()` — connection helpers
- `_format_data_with_semantic_types()` — semantic formatting
- `_execute_query()` — query execution

Class stays named `OmahaService` (or `QueryEngine` — see open question below) and moves to `app/services/query/engine.py`.

### Query Builder: `app/services/legacy/financial/query_builder.py` → `app/services/query/builder.py`

The `SemanticQueryBuilder` is generic — it builds queries with semantic type awareness. Retain as-is, just move path.

### Connectors retained
- `sql_connector.py` (SQLite + MySQL)
- `csv_connector.py`
- `rest_connector.py`
- `mongodb_connector.py`
- `base.py`, `registry.py`

### Templates retained
- `configs/templates/retail.yaml` — stays as industry template for modeling
- Move from `configs/templates/` to `app/services/ontology/templates/` for co-location

## Naming Decisions (Confirmed)

### `OmahaService` → `QueryEngine`
The class name will change as part of the move from `legacy/financial/omaha.py` to `query/engine.py`. "Omaha" is the project name, not a description of the class's responsibility. `QueryEngine` is the right name for a generic platform's query primitive. This rename affects ~20 import sites; doing it now (alongside the path move) keeps the cost low.

### `frontend/src/pages/legacy/` → `frontend/src/pages/shared/`
After deleting the 2 financial-specific files (`Explorer.tsx`, `QueryHistory.tsx`), the remaining 6 files (DatasourceManager, OntologyEditor, MembersManager, AuditLogViewer, PipelineManager, ObjectExplorer) are reusable business components imported by v2 pages — they are not legacy. Rename the directory and update the 10 import paths.

## Known Deferred Architecture Debt

This spec deliberately scopes itself to **mechanical deletion and renaming**. It does not solve three deeper architectural problems that we are aware of:

### 1. `engine.py` is a 5-responsibility class
After removing the financial methods, the retained `QueryEngine` (~400 lines) still mixes: YAML parsing, ontology building, query construction, connector dispatch, result formatting. Some of these responsibilities already have homes elsewhere (`services/ontology/`, `services/semantic/formatter.py`) and the engine should delegate rather than reimplement.

**Why deferred:** Decomposing it now would balloon this spec's scope from 1–2 days to 1–2 weeks. Better to land the rename + delete first, then tackle engine decomposition as its own focused spec.

### 2. Frontend v2 pages are 1-line wrappers
`pages/apps/DatasourcePage.tsx`, `pages/apps/PipelinesPage.tsx`, `pages/settings/SettingsPage.tsx`, etc. each consist of a single `import` line and a single render. The v2 page restructure left the actual implementation in the (renamed) `shared/` directory. Renaming `legacy/` → `shared/` makes the naming honest, but does not eliminate the wrapper-page indirection.

**Why deferred:** Eliminating wrappers requires deciding the v2 page model: do pages own their content, or are they just route mountpoints? That is a frontend architecture question separate from removing the financial vertical.

### 3. No verticals extension point
If retail, manufacturing, or SaaS-connector verticals (用友/钉钉/有赞) are added in the future, there is no clear "vertical insertion point" in the architecture. They could end up replicating the `legacy/financial/` pattern.

**Why deferred:** Designing a verticals extension point is YAGNI today — there is no concrete second vertical to validate the design against. Defer until the first new vertical actually appears.

## Execution Order

Phase 1 (backend deletions — no frontend changes):
1. Drop `_legacy_chat_service.py` + remove re-export shim
2. Delete financial API routes + remove router registrations
3. Delete financial models + schemas + Alembic migration
4. Delete `ontology_cache_service.py`
5. Delete `tushare_connector.py` + deregister
6. Delete financial config YAML + `_paths.py` cleanup
7. Clean `omaha.py` — remove Tushare/financial methods
8. Move cleaned `omaha.py` → `app/services/query/engine.py`, rename class `OmahaService` → `QueryEngine`
9. Move `query_builder.py` → `app/services/query/builder.py`
10. Delete MCP `screen_stocks` + DataHub integration
11. Clean `app/config.py`, `.env.example`, health check
12. Update all imports (~70 files), including `OmahaService` → `QueryEngine` rename (~20 sites)
13. Run full test suite

Phase 2 (frontend + naming):
14. Delete `Explorer.tsx`, `QueryHistory.tsx`, remove routes
15. Rename `pages/legacy/` → `pages/shared/`, update imports
16. Frontend tsc + build verification

Deferred (separate spec when needed):
- Decompose `engine.py` into single-responsibility modules
- Eliminate frontend wrapper-page pattern
- Verticals extension point

## Success Criteria

- `grep -rn "tushare\|Tushare\|TUSHARE" backend/app/` returns 0 hits
- `grep -rn "watchlist\|Watchlist" backend/app/` returns 0 hits (except generic model references)
- `grep -rn "CachedStock\|CachedFinancial\|cached_stock" backend/app/` returns 0 hits
- `grep -rn "screen_stocks" backend/app/` returns 0 hits
- `grep -rn "datahub\|DataHub\|DATAHUB" backend/app/` returns 0 hits
- `grep -rn "OmahaService" backend/app/` returns 0 hits
- No file path contains `legacy/financial` or `pages/legacy`
- Backend test suite passes
- Frontend tsc + build passes
- `app/services/query/engine.py::QueryEngine` exists and is importable
- `app/services/query/builder.py` exists and is importable
- All scenario scripts (`verify_modeling_scenario.py`, `verify_complex_scenario.py`) still pass
