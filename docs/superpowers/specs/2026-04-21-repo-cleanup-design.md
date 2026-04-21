# Repository Cleanup and Reorganization Design

## Objective

Clean the repository aggressively while preserving the complete current production/demo capability. Remove legacy code, stale documentation, temporary scripts, generated artifacts, duplicate reports, and unused tests that no longer support the current runtime, build, deployment, or demo paths. Reorganize the repository so the top level clearly reflects active code, configuration, deployment, and user-facing documentation.

## Scope

This cleanup covers:
- repository root files and folders
- backend code, tests, scripts, and reports
- frontend pages and components that may no longer be referenced
- configs and local test config files
- deployment scripts and deployment documentation
- docs, specs, plans, reports, and presentation materials

This cleanup does not change product requirements or add new features. It is a repository reduction and organization pass constrained by preserving the current live/demo behavior.

## Preservation Rule

The preservation rule is strict:

> Keep everything required for the complete current live/demo capability. Remove or archive everything else.

A file is considered active only if it is part of at least one of these paths:
- runtime path: imported or executed by the backend, frontend, or MCP server
- build path: needed for install, build, test, or packaging
- deployment path: required by the currently used deployment flow
- demo path: required to run the current demo or operator workflow
- maintenance path: necessary setup or operational documentation for current usage

Age is not a reason to delete. Lack of present use is.

## Active Capability Baseline

The cleanup must preserve the current end-to-end product capability, including:
- backend API service and database migrations
- authentication, project management, assets, chat, watchlist, ontology, query, and public query surfaces that are still wired into current routes
- MCP server startup and the active MCP tools
- current frontend routes and pages still reachable from the application shell
- active financial ontology configuration and required environment-variable-based config loading
- currently used deployment scripts and service definitions
- minimum operator documentation needed to run, deploy, and troubleshoot the system

## Cleanup Strategy

Use a whitelist-first strategy.

### Phase 1: Inventory active surfaces
Identify the files and directories that are still active by tracing:
- FastAPI route registration and imports
- frontend routing and page/component imports
- MCP tool registration and execution paths
- deployment entrypoints and referenced scripts
- config files actually referenced by code, docs, or deployment
- tests that still validate active behavior

### Phase 2: Mark removable candidates
Classify removable items into explicit groups:
1. Generated artifacts and local clutter
2. Root-level one-off tests and ad hoc configs
3. Historical reports and milestone summaries
4. Stale plans/specs no longer needed for operating the current system
5. Unreferenced backend code
6. Unreferenced frontend pages/components/services
7. Deployment leftovers not used by the current path
8. Presentation materials and non-product documents

### Phase 3: Restructure repository layout
After deletion decisions are validated, normalize the repository layout so the top level remains concise and intentional.

## Planned Target Structure

The desired top-level structure is:

- `backend/` — application code, migrations, backend scripts, backend tests
- `frontend/` — web application code
- `configs/` — active ontology and environment-backed config files
- `deployment/` — active deployment scripts and service definitions
- `docs/` — concise operating docs and a small set of current design references
- `.claude/` — Claude Code project configuration and skills
- root files only for project entrypoints and essential instructions

The root directory should not contain:
- ad hoc test scripts
- milestone reports
- archived tarballs
- generated files
- duplicate setup notes
- experiment-specific presentation documents

## Candidate Removal Categories

These categories are expected to be aggressively reduced.

### 1. Generated and local artifacts
Examples observed in the repository:
- `__pycache__/`
- `backend/tests/__pycache__/`
- `.pytest_cache/`
- `.DS_Store`
- local database files not required for version control
- archive files such as `*.tar.gz`

### 2. Root-level one-off validation files
Examples observed in the repository root:
- `test_aggregate_api.py`
- `test_all_computed_properties.py`
- `test_batch_query.py`
- `test_default_filters.py`
- `test_default_filters_v2.py`
- `test_end_to_end.py`
- `test_financial_ontology_cloud.py`
- `test_join_api.sh`
- `test_mcp_tools.py`
- `test_new_semantic_types.py`
- `test_ontology_direct.py`
- `test_ontology_validation.py`
- `test_performance_monitoring.py`
- `test_phase3_real_scenario.py`
- `test_phase4_financial_reports.py`
- `test_public_query.py`
- temporary yaml files such as `test_config.yaml`, `test_local.yaml`, `test_tushare_config.yaml`

These should either be deleted, moved into structured test locations, or kept only if they still cover active production/demo behavior and cannot be replaced by `backend/tests/**`.

### 3. Historical reports and status documents
Examples observed at the root and in `docs/`:
- `COMPLETE_REPORT.md`
- `EXECUTION_SUMMARY.md`
- `FINAL_DELIVERY.md`
- `GRANULARITY_FEATURE_TEST_REPORT.md`
- `ONTOLOGY_COMPLETE.md`
- `ONTOLOGY_REDESIGN_SUCCESS.md`
- `ONTOLOGY_REFINEMENT_REPORT.md`
- `docs/DEPLOYMENT_STATUS.md`
- `docs/DEPLOYMENT_VERIFICATION.md`
- `docs/MCP_FINAL_STATUS.md`
- `docs/FINAL_ONTOLOGY_REPORT.md`
- `docs/ONTOLOGY_MAXIMIZATION_REPORT.md`
- `docs/ONTOLOGY_VALUE_REPORT.md`
- `docs/test_reports/**`

These are not part of the runtime product and should be removed unless one of them is still the canonical operator document.

### 4. Old planning/spec materials
Examples observed:
- `docs/superpowers/specs/**`
- `docs/superpowers/plans/**`
- `docs/design/**`
- `docs/implementation/**`

The cleanup should retain only documents that are still needed to understand or operate the current system. Historical execution records, interim plans, scratch files, and obsolete design docs should be deleted.

### 5. Presentation and non-product collateral
Examples observed:
- `docs/university-talk.md`
- `docs/omaha-intro.md`
- `portfolio_design.md`
- `ontology_evaluation.md`

These should be removed unless they are actively part of the current demo workflow.

## Reorganization Rules

### Backend
- Keep runtime code under `backend/app/**`
- Keep migrations under `backend/alembic/**`
- Keep only active operational scripts under `backend/scripts/**`
- Consolidate backend tests under `backend/tests/**`
- Remove standalone backend test reports and experimental validation files from `backend/`

### Frontend
- Keep only pages reachable from the current app routes
- Remove dead components, services, and type definitions that are no longer imported
- Preserve current route behavior and navigation structure

### Configs
- Keep active ontology configs only
- Remove test-only configs from the repository root
- Prefer environment-variable-backed secrets over checked-in tokens

### Deployment
- Keep only the currently used deployment chain
- Remove duplicate or abandoned deploy entrypoints once current references are confirmed
- Preserve service/unit files and reverse-proxy config still used in operations

### Documentation
Keep only:
- `README.md`
- `LOCAL_SETUP.md`
- `RUNNING.md`
- one concise API/MCP usage guide if still relevant
- one concise deployment guide if still relevant
- a minimal number of current architecture/design notes when they are still operationally useful

Delete duplicate summaries, completion reports, milestone reports, and temporary validation writeups.

## Safety Rules

The cleanup must not rely on filename age alone. Before deleting code or configs, verify current usage by one or more of:
- import/reference search
- route registration inspection
- frontend route and component reference inspection
- deployment script reference tracing
- config file reference tracing
- test relevance review

For risky items, prefer a staged move or explicit verification before deletion.

## Validation Requirements

After cleanup, validate the repository by running or confirming:
- backend imports still resolve
- FastAPI app still starts
- MCP server still starts
- frontend still builds
- active routes/pages still exist
- active config loads still work
- active deployment files referenced by current docs/scripts still exist
- selected core tests for active functionality still pass

## Success Criteria

The cleanup is successful when all of the following are true:
- the current live/demo capability still works
- the repository root contains only intentional entrypoint files
- obsolete reports, archives, and one-off validation files are removed
- docs are reduced to current operational guidance
- active tests live in structured test locations
- code no longer contains obviously dead frontend/backend entrypoints
- config and deployment files clearly represent the current operating path

## Expected Deliverable

The implementation should produce:
- a substantially smaller and clearer repository
- fewer duplicate documents and scattered scripts
- a clean root directory
- a single obvious place for tests, configs, deployment, and operator docs
- preserved current product behavior without historical clutter
