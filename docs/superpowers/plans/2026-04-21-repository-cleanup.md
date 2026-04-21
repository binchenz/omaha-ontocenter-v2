# Repository Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove legacy repository clutter while preserving the complete current live/demo capability across backend, frontend, MCP, deployment, and operator workflows.

**Architecture:** This cleanup uses a whitelist-first approach. First map active runtime, build, deployment, and documentation entrypoints from the current application wiring, then delete or relocate everything not required by those paths, and finally verify the preserved surfaces still build and start. The implementation keeps code changes minimal and focuses on repository reduction, dead-file removal, test consolidation, and documentation normalization.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, React 18, TypeScript, Vite, pytest, MCP

---

## File Responsibility Map

### Active runtime and build entrypoints to preserve
- `backend/app/main.py` — FastAPI startup and route mounting
- `backend/app/api/__init__.py` — backend API router registration
- `backend/app/mcp/server.py` — MCP server startup and tool registration
- `backend/app/mcp/tools.py` — MCP tool implementations
- `backend/alembic/**` — database migrations
- `backend/requirements.txt` — backend runtime/test dependencies
- `frontend/src/App.tsx` — frontend route definitions
- `frontend/src/components/Layout/Sidebar.tsx` — visible navigation surface for current pages
- `frontend/package.json` — frontend build commands
- `configs/financial_stock_analysis.yaml` — active ontology config used for financial flows
- `deployment/README.md` and scripts it references — currently documented deployment path
- `README.md`, `LOCAL_SETUP.md`, `RUNNING.md` — operator/developer entrypoint docs to normalize

### Candidate removal or consolidation targets
- Root-level reports, archives, temp configs, and one-off tests
- `docs/test_reports/**`, most `docs/superpowers/plans/**`, most `docs/superpowers/specs/**`, `docs/design/**`, `docs/implementation/**`
- Standalone backend reports and e2e JSON artifacts in `backend/`
- Dead frontend pages/components/services not reachable from `frontend/src/App.tsx` or imports beneath current pages
- Deployment scripts not referenced by the chosen deployment path

### Likely files to modify
- `README.md`
- `LOCAL_SETUP.md`
- `RUNNING.md`
- `.gitignore`
- Possibly `deployment/README.md`
- Possibly selected test files under `backend/tests/**`

### Likely files to create
- `docs/repository-structure.md`
- `backend/tests/test_repository_active_surfaces.py`

---

### Task 1: Lock active backend, frontend, MCP, and deployment surfaces

**Files:**
- Modify: `backend/app/main.py:1-45`
- Modify: `backend/app/api/__init__.py:1-18`
- Modify: `backend/app/mcp/server.py:1-220`
- Modify: `frontend/src/App.tsx:1-37`
- Modify: `frontend/src/components/Layout/Sidebar.tsx:1-66`
- Modify: `deployment/README.md:1-137`
- Test: `backend/tests/test_repository_active_surfaces.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_current_active_surfaces_are_documented():
    root = Path(__file__).resolve().parents[2]

    required_files = [
        "backend/app/main.py",
        "backend/app/api/__init__.py",
        "backend/app/mcp/server.py",
        "frontend/src/App.tsx",
        "frontend/src/components/Layout/Sidebar.tsx",
        "deployment/README.md",
        "configs/financial_stock_analysis.yaml",
    ]

    missing = [path for path in required_files if not (root / path).exists()]
    assert missing == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py -v`
Expected: FAIL with `file or directory not found: tests/test_repository_active_surfaces.py`

- [ ] **Step 3: Write minimal implementation**

Create `backend/tests/test_repository_active_surfaces.py` with:

```python
from pathlib import Path


def test_current_active_surfaces_are_documented():
    root = Path(__file__).resolve().parents[2]

    required_files = [
        "backend/app/main.py",
        "backend/app/api/__init__.py",
        "backend/app/mcp/server.py",
        "frontend/src/App.tsx",
        "frontend/src/components/Layout/Sidebar.tsx",
        "deployment/README.md",
        "configs/financial_stock_analysis.yaml",
    ]

    missing = [path for path in required_files if not (root / path).exists()]
    assert missing == []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_repository_active_surfaces.py
git commit -m "test: lock active repository entrypoints"
```

### Task 2: Remove generated artifacts and root-level archive clutter

**Files:**
- Modify: `.gitignore:1-200`
- Delete: `.DS_Store`
- Delete: `.pytest_cache/`
- Delete: `__pycache__/`
- Delete: `backend/tests/__pycache__/`
- Delete: `backend.tar.gz`
- Delete: `backend_perf_update.tar.gz`
- Delete: `watchlist_update.tar.gz`
- Delete: `backend/e2e_test_report_20260317_022321.json`
- Delete: `backend/e2e_test_report_20260317_022321_revalidated.json`
- Delete: `backend/focused_e2e_report_20260317_022910.json`
- Test: `backend/tests/test_repository_active_surfaces.py`

- [ ] **Step 1: Write the failing test**

Add this test to `backend/tests/test_repository_active_surfaces.py`:

```python
def test_repository_root_excludes_generated_and_archive_clutter():
    root = Path(__file__).resolve().parents[2]

    disallowed_paths = [
        ".DS_Store",
        ".pytest_cache",
        "__pycache__",
        "backend.tar.gz",
        "backend_perf_update.tar.gz",
        "watchlist_update.tar.gz",
        "backend/e2e_test_report_20260317_022321.json",
        "backend/e2e_test_report_20260317_022321_revalidated.json",
        "backend/focused_e2e_report_20260317_022910.json",
    ]

    present = [path for path in disallowed_paths if (root / path).exists()]
    assert present == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_repository_root_excludes_generated_and_archive_clutter -v`
Expected: FAIL showing the currently present clutter paths

- [ ] **Step 3: Write minimal implementation**

Apply these changes:

```gitignore
# macOS
.DS_Store

# Python cache
__pycache__/
*.py[cod]
.pytest_cache/

# Local archives and generated reports
*.tar.gz
backend/*e2e*_report*.json
backend/focused_e2e_report_*.json
```

Delete the listed files and directories exactly:

```bash
rm -rf /Users/wangfushuaiqi/omaha_ontocenter/.DS_Store \
  /Users/wangfushuaiqi/omaha_ontocenter/.pytest_cache \
  /Users/wangfushuaiqi/omaha_ontocenter/__pycache__ \
  /Users/wangfushuaiqi/omaha_ontocenter/backend/tests/__pycache__
rm -f /Users/wangfushuaiqi/omaha_ontocenter/backend.tar.gz \
  /Users/wangfushuaiqi/omaha_ontocenter/backend_perf_update.tar.gz \
  /Users/wangfushuaiqi/omaha_ontocenter/watchlist_update.tar.gz \
  /Users/wangfushuaiqi/omaha_ontocenter/backend/e2e_test_report_20260317_022321.json \
  /Users/wangfushuaiqi/omaha_ontocenter/backend/e2e_test_report_20260317_022321_revalidated.json \
  /Users/wangfushuaiqi/omaha_ontocenter/backend/focused_e2e_report_20260317_022910.json
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_repository_root_excludes_generated_and_archive_clutter -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add .gitignore backend/tests/test_repository_active_surfaces.py
git add -u .
git commit -m "chore: remove generated repository clutter"
```

### Task 3: Eliminate root-level one-off tests and test configs by consolidating active coverage

**Files:**
- Modify: `backend/tests/test_default_filters.py:1-260`
- Modify: `backend/tests/integration/test_phase31_mcp.py:1-260`
- Modify: `backend/tests/test_tushare_integration.py:1-260`
- Delete: `test_aggregate_api.py`
- Delete: `test_all_computed_properties.py`
- Delete: `test_batch_query.py`
- Delete: `test_default_filters.py`
- Delete: `test_default_filters_v2.py`
- Delete: `test_end_to_end.py`
- Delete: `test_financial_ontology_cloud.py`
- Delete: `test_join_api.sh`
- Delete: `test_mcp_tools.py`
- Delete: `test_new_semantic_types.py`
- Delete: `test_ontology_direct.py`
- Delete: `test_ontology_validation.py`
- Delete: `test_performance_monitoring.py`
- Delete: `test_phase3_real_scenario.py`
- Delete: `test_phase4_financial_reports.py`
- Delete: `test_public_query.py`
- Delete: `test_config.yaml`
- Delete: `test_local.yaml`
- Delete: `test_tushare_config.yaml`
- Test: `backend/tests/test_repository_active_surfaces.py`

- [ ] **Step 1: Write the failing test**

Add this test to `backend/tests/test_repository_active_surfaces.py`:

```python
def test_root_level_one_off_tests_and_temp_configs_are_absent():
    root = Path(__file__).resolve().parents[2]

    disallowed_paths = [
        "test_aggregate_api.py",
        "test_all_computed_properties.py",
        "test_batch_query.py",
        "test_default_filters.py",
        "test_default_filters_v2.py",
        "test_end_to_end.py",
        "test_financial_ontology_cloud.py",
        "test_join_api.sh",
        "test_mcp_tools.py",
        "test_new_semantic_types.py",
        "test_ontology_direct.py",
        "test_ontology_validation.py",
        "test_performance_monitoring.py",
        "test_phase3_real_scenario.py",
        "test_phase4_financial_reports.py",
        "test_public_query.py",
        "test_config.yaml",
        "test_local.yaml",
        "test_tushare_config.yaml",
    ]

    present = [path for path in disallowed_paths if (root / path).exists()]
    assert present == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_root_level_one_off_tests_and_temp_configs_are_absent -v`
Expected: FAIL showing the remaining root-level test and config files

- [ ] **Step 3: Write minimal implementation**

First, move any still-useful assertions from root-level files into structured tests under `backend/tests/**`. Use these exact additions:

```python
# backend/tests/test_default_filters.py

def test_default_filters_apply_to_active_query_builder():
    config_yaml = """
ontology:
  objects:
    - name: TestObject
      table: test_table
      default_filters:
        - field: platform_id
          operator: "IS NOT NULL"
      properties:
        - name: platform_id
          column: platform_id
          type: string
        - name: city
          column: city
          type: string
"""
    builder = SemanticQueryBuilder(config_yaml, "TestObject")
    query, params = builder.build(
        selected_columns=["city"],
        filters=[{"field": "city", "operator": "=", "value": "上海"}],
        joins=None,
        limit=10,
        db_type="mysql",
    )
    assert "platform_id IS NOT NULL" in query
    assert "city = %s" in query
    assert "上海" in params

# backend/tests/integration/test_phase31_mcp.py

def test_mcp_query_path_still_returns_expected_shape():
    from app.mcp.tools import list_objects
    config = "datasources: []\nontology:\n  objects:\n    - name: Product\n      datasource: x\n      table: t\n      primary_key: id\n      properties: []"
    result = list_objects(config)
    assert "objects" in result
    names = [obj["name"] if isinstance(obj, dict) else obj for obj in result["objects"]]
    assert "Product" in names

# backend/tests/test_tushare_integration.py

def test_financial_config_uses_environment_token():
    from pathlib import Path
    config_path = Path(__file__).resolve().parents[2] / "configs" / "financial_stock_analysis.yaml"
    text = config_path.read_text(encoding="utf-8")
    assert "${TUSHARE_TOKEN}" in text
    assert "044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90" not in text
```

Then delete the root-level files listed above exactly.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_root_level_one_off_tests_and_temp_configs_are_absent -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_default_filters.py backend/tests/integration/test_phase31_mcp.py backend/tests/test_tushare_integration.py backend/tests/test_repository_active_surfaces.py
git add -u .
git commit -m "test: consolidate active coverage under backend tests"
```

### Task 4: Reduce docs to current operational guidance only

**Files:**
- Modify: `README.md:1-200`
- Modify: `LOCAL_SETUP.md:1-200`
- Modify: `RUNNING.md:1-200`
- Modify: `deployment/README.md:1-200`
- Create: `docs/repository-structure.md`
- Delete: `COMPLETE_REPORT.md`
- Delete: `EXECUTION_SUMMARY.md`
- Delete: `FINAL_DELIVERY.md`
- Delete: `GRANULARITY_FEATURE_TEST_REPORT.md`
- Delete: `ONTOLOGY_COMPLETE.md`
- Delete: `ONTOLOGY_REDESIGN_SUCCESS.md`
- Delete: `ONTOLOGY_REFINEMENT_REPORT.md`
- Delete: `docs/DEPLOYMENT_STATUS.md`
- Delete: `docs/DEPLOYMENT_VERIFICATION.md`
- Delete: `docs/MCP_FINAL_STATUS.md`
- Delete: `docs/FINAL_ONTOLOGY_REPORT.md`
- Delete: `docs/ONTOLOGY_MAXIMIZATION_REPORT.md`
- Delete: `docs/ONTOLOGY_VALUE_REPORT.md`
- Delete: `docs/test_reports/phase1_chat_test_cases.md`
- Delete: `docs/test_reports/phase1_chat_test_results.md`
- Delete: `docs/test_reports/phase2_completion_report.md`
- Delete: `docs/test_reports/phase2_test_scenarios.md`
- Delete: `docs/test_reports/phase3_completion_report.md`
- Delete: `docs/test_reports/financial_ontology_skill_status.md`
- Delete: `docs/test_reports/mcp_resolution_report.md`
- Delete: `docs/university-talk.md`
- Delete: `docs/omaha-intro.md`
- Delete: `portfolio_design.md`
- Delete: `ontology_evaluation.md`
- Test: `backend/tests/test_repository_active_surfaces.py`

- [ ] **Step 1: Write the failing test**

Add this test to `backend/tests/test_repository_active_surfaces.py`:

```python
def test_docs_are_reduced_to_current_operational_materials():
    root = Path(__file__).resolve().parents[2]

    required_files = [
        "README.md",
        "LOCAL_SETUP.md",
        "RUNNING.md",
        "deployment/README.md",
        "docs/repository-structure.md",
    ]
    missing = [path for path in required_files if not (root / path).exists()]

    removed_files = [
        "COMPLETE_REPORT.md",
        "EXECUTION_SUMMARY.md",
        "FINAL_DELIVERY.md",
        "GRANULARITY_FEATURE_TEST_REPORT.md",
        "ONTOLOGY_COMPLETE.md",
        "ONTOLOGY_REDESIGN_SUCCESS.md",
        "ONTOLOGY_REFINEMENT_REPORT.md",
        "docs/DEPLOYMENT_STATUS.md",
        "docs/DEPLOYMENT_VERIFICATION.md",
        "docs/MCP_FINAL_STATUS.md",
        "docs/FINAL_ONTOLOGY_REPORT.md",
        "docs/ONTOLOGY_MAXIMIZATION_REPORT.md",
        "docs/ONTOLOGY_VALUE_REPORT.md",
        "docs/university-talk.md",
        "docs/omaha-intro.md",
        "portfolio_design.md",
        "ontology_evaluation.md",
    ]
    present = [path for path in removed_files if (root / path).exists()]

    assert missing == []
    assert present == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_docs_are_reduced_to_current_operational_materials -v`
Expected: FAIL because `docs/repository-structure.md` does not exist and legacy docs still exist

- [ ] **Step 3: Write minimal implementation**

Rewrite the surviving docs to reflect the current system:

```markdown
# README.md

# Omaha OntoCenter

Current repository layout:
- `backend/` FastAPI API, MCP server, models, services, migrations, tests
- `frontend/` React app for login, projects, ontology map, and watchlist
- `configs/` active ontology configs
- `deployment/` active deployment scripts
- `docs/` concise operator and structure docs

Primary routes currently in use:
- frontend: `/login`, `/register`, `/projects`, `/projects/:id`, `/projects/:id/map`, `/watchlist`
- backend: `/api/v1/*`, `/api/public/auth/*`, `/api/public/v1/*`, `/health`
```

```markdown
# docs/repository-structure.md

# Repository Structure

## Keep at root
- `README.md`
- `LOCAL_SETUP.md`
- `RUNNING.md`
- `CLAUDE.md`
- `.env.example`

## Active directories
- `backend/`
- `frontend/`
- `configs/`
- `deployment/`
- `docs/`
- `.claude/`

## Cleanup rule
Anything outside the active runtime, build, deployment, or operator path should not live at the repository root.
```

Delete the listed legacy documents exactly.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_docs_are_reduced_to_current_operational_materials -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add README.md LOCAL_SETUP.md RUNNING.md deployment/README.md docs/repository-structure.md backend/tests/test_repository_active_surfaces.py
git add -u .
git commit -m "docs: reduce repository docs to active guidance"
```

### Task 5: Remove obsolete planning artifacts and keep only active design references

**Files:**
- Delete: `docs/design/design_improvement_roadmap.md`
- Delete: `docs/design/p0_implementation_plan.md`
- Delete: `docs/design/phase3_semantic_enhancements.md`
- Delete: `docs/implementation/p0_completion_report.md`
- Delete: `docs/superpowers/plans/2026-03-15-phase3.1-mcp-server.md`
- Delete: `docs/superpowers/plans/2026-03-15-phase3.2-chat-interface.md`
- Delete: `docs/superpowers/plans/2026-03-16-ontology-redesign-audit.md`
- Delete: `docs/superpowers/plans/2026-03-16-ontology-redesign.md`
- Delete: `docs/superpowers/plans/2026-03-17-FINAL-IMPLEMENTATION-REPORT.md`
- Delete: `docs/superpowers/plans/2026-03-17-ontology-redesign-phase2-completion.md`
- Delete: `docs/superpowers/plans/2026-03-17-ontology-redesign-phase3-index.md`
- Delete: `docs/superpowers/plans/2026-03-17-ontology-redesign-phase3-issues.md`
- Delete: `docs/superpowers/plans/2026-03-17-ontology-redesign-phase3-summary.md`
- Delete: `docs/superpowers/plans/2026-03-17-ontology-redesign-phase3-test-data.md`
- Delete: `docs/superpowers/plans/2026-03-17-ontology-redesign-phase3-validation-report.md`
- Delete: `docs/superpowers/plans/2026-03-17-phase3-fixes-summary.md`
- Delete: `docs/superpowers/plans/2026-03-26-financial-data-objects-phase1.md`
- Delete: `docs/superpowers/plans/2026-03-26-financial-data-objects-phase2.md`
- Delete: `docs/superpowers/plans/2026-03-27-cloud-deployment.md`
- Delete: `docs/superpowers/plans/2026-03-29-frontend-redesign-plan-a.md`
- Delete: `docs/superpowers/plans/2026-03-29-frontend-redesign-plan-b.md`
- Delete: `docs/superpowers/plans/test.md`
- Delete: `docs/superpowers/specs/2026-03-15-phase3-design.md`
- Delete: `docs/superpowers/specs/2026-03-16-phase4-semantic-layer.md`
- Delete: `docs/superpowers/specs/2026-03-26-financial-data-objects-design.md`
- Delete: `docs/superpowers/specs/2026-03-27-cloud-deployment-design.md`
- Delete: `docs/superpowers/specs/2026-03-29-frontend-redesign-design.md`
- Delete: `docs/.DS_Store`
- Test: `backend/tests/test_repository_active_surfaces.py`

- [ ] **Step 1: Write the failing test**

Add this test to `backend/tests/test_repository_active_surfaces.py`:

```python
def test_only_current_design_references_remain_under_docs_superpowers():
    root = Path(__file__).resolve().parents[2]

    required_files = [
        "docs/superpowers/specs/2026-04-21-repo-cleanup-design.md",
        "docs/superpowers/specs/2026-03-29-ontology-map-design.md",
        "docs/superpowers/specs/2026-04-12-university-talk-design.md",
        "docs/superpowers/plans/2026-03-29-ontology-map-plan.md",
        "docs/superpowers/plans/2026-04-12-university-talk.md",
    ]
    missing = [path for path in required_files if not (root / path).exists()]

    removed_files = [
        "docs/design/design_improvement_roadmap.md",
        "docs/design/p0_implementation_plan.md",
        "docs/design/phase3_semantic_enhancements.md",
        "docs/implementation/p0_completion_report.md",
        "docs/superpowers/plans/2026-03-15-phase3.1-mcp-server.md",
        "docs/superpowers/plans/2026-03-15-phase3.2-chat-interface.md",
        "docs/superpowers/plans/2026-03-16-ontology-redesign-audit.md",
        "docs/superpowers/plans/2026-03-16-ontology-redesign.md",
        "docs/superpowers/plans/2026-03-17-FINAL-IMPLEMENTATION-REPORT.md",
        "docs/superpowers/plans/2026-03-17-ontology-redesign-phase2-completion.md",
        "docs/superpowers/plans/2026-03-17-ontology-redesign-phase3-index.md",
        "docs/superpowers/plans/2026-03-17-ontology-redesign-phase3-issues.md",
        "docs/superpowers/plans/2026-03-17-ontology-redesign-phase3-summary.md",
        "docs/superpowers/plans/2026-03-17-ontology-redesign-phase3-test-data.md",
        "docs/superpowers/plans/2026-03-17-ontology-redesign-phase3-validation-report.md",
        "docs/superpowers/plans/2026-03-17-phase3-fixes-summary.md",
        "docs/superpowers/plans/2026-03-26-financial-data-objects-phase1.md",
        "docs/superpowers/plans/2026-03-26-financial-data-objects-phase2.md",
        "docs/superpowers/plans/2026-03-27-cloud-deployment.md",
        "docs/superpowers/plans/2026-03-29-frontend-redesign-plan-a.md",
        "docs/superpowers/plans/2026-03-29-frontend-redesign-plan-b.md",
        "docs/superpowers/plans/test.md",
        "docs/superpowers/specs/2026-03-15-phase3-design.md",
        "docs/superpowers/specs/2026-03-16-phase4-semantic-layer.md",
        "docs/superpowers/specs/2026-03-26-financial-data-objects-design.md",
        "docs/superpowers/specs/2026-03-27-cloud-deployment-design.md",
        "docs/superpowers/specs/2026-03-29-frontend-redesign-design.md",
        "docs/.DS_Store",
    ]
    present = [path for path in removed_files if (root / path).exists()]

    assert missing == []
    assert present == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_only_current_design_references_remain_under_docs_superpowers -v`
Expected: FAIL showing the still-present historical plan/spec files

- [ ] **Step 3: Write minimal implementation**

Delete the listed historical planning and report files exactly. Keep only the current references that still match the active system and this cleanup work:

```text
docs/superpowers/specs/2026-04-21-repo-cleanup-design.md
docs/superpowers/specs/2026-03-29-ontology-map-design.md
docs/superpowers/specs/2026-04-12-university-talk-design.md
docs/superpowers/plans/2026-03-29-ontology-map-plan.md
docs/superpowers/plans/2026-04-12-university-talk.md
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_only_current_design_references_remain_under_docs_superpowers -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_repository_active_surfaces.py
git add -u docs
git commit -m "docs: remove obsolete planning artifacts"
```

### Task 6: Remove dead frontend surfaces not reachable from current routes

**Files:**
- Modify: `frontend/src/App.tsx:1-37`
- Modify: `frontend/src/components/Layout/Sidebar.tsx:1-66`
- Delete: `frontend/src/pages/AggregateQuery.tsx`
- Delete: `frontend/src/pages/AssetList.tsx`
- Delete: `frontend/src/pages/ChatAgent.tsx`
- Delete: `frontend/src/pages/ChatWithSessions.tsx`
- Delete: `frontend/src/pages/ObjectExplorer.tsx`
- Delete: `frontend/src/pages/OntologyViewer.tsx`
- Delete: `frontend/src/pages/QueryBuilder.tsx`
- Delete: `frontend/src/pages/QueryHistory.tsx`
- Delete: `frontend/src/pages/SemanticEditor.tsx`
- Delete: `frontend/src/components/ApiKeyManager.tsx`
- Delete: `frontend/src/components/LineageGraph.tsx`
- Delete: `frontend/src/components/chat/ChartRenderer.tsx`
- Delete: `frontend/src/components/chat/ChatMessage.tsx`
- Delete: `frontend/src/components/chat/DataTable.tsx`
- Delete: `frontend/src/components/semantic/AgentPreview.tsx`
- Delete: `frontend/src/components/semantic/FormulaBuilder.tsx`
- Delete: `frontend/src/components/semantic/ObjectList.tsx`
- Delete: `frontend/src/components/semantic/PropertyEditor.tsx`
- Delete: `frontend/src/services/apiKeyService.ts`
- Delete: `frontend/src/services/asset.ts`
- Delete: `frontend/src/services/chatApi.ts`
- Delete: `frontend/src/services/ontology.ts`
- Delete: `frontend/src/services/query.ts`
- Delete: `frontend/src/services/queryHistory.ts`
- Delete: `frontend/src/services/semanticApi.ts`
- Delete: `frontend/src/types/chat.ts`
- Delete: `frontend/src/types/semantic.ts`
- Test: `frontend/package.json`

- [ ] **Step 1: Write the failing test**

Add this test to `backend/tests/test_repository_active_surfaces.py`:

```python
def test_frontend_keeps_only_currently_routed_pages_and_supporting_modules():
    root = Path(__file__).resolve().parents[2]

    required_files = [
        "frontend/src/App.tsx",
        "frontend/src/pages/Login.tsx",
        "frontend/src/pages/Register.tsx",
        "frontend/src/pages/ProjectList.tsx",
        "frontend/src/pages/ProjectDetail.tsx",
        "frontend/src/pages/OntologyMap.tsx",
        "frontend/src/pages/Watchlist.tsx",
        "frontend/src/components/Layout/MainLayout.tsx",
        "frontend/src/components/Layout/Sidebar.tsx",
        "frontend/src/components/PrivateRoute.tsx",
    ]
    missing = [path for path in required_files if not (root / path).exists()]

    removed_files = [
        "frontend/src/pages/AggregateQuery.tsx",
        "frontend/src/pages/AssetList.tsx",
        "frontend/src/pages/ChatAgent.tsx",
        "frontend/src/pages/ChatWithSessions.tsx",
        "frontend/src/pages/ObjectExplorer.tsx",
        "frontend/src/pages/OntologyViewer.tsx",
        "frontend/src/pages/QueryBuilder.tsx",
        "frontend/src/pages/QueryHistory.tsx",
        "frontend/src/pages/SemanticEditor.tsx",
        "frontend/src/components/ApiKeyManager.tsx",
        "frontend/src/components/LineageGraph.tsx",
    ]
    present = [path for path in removed_files if (root / path).exists()]

    assert missing == []
    assert present == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_frontend_keeps_only_currently_routed_pages_and_supporting_modules -v`
Expected: FAIL showing the extra page/component files still present

- [ ] **Step 3: Write minimal implementation**

Before deleting, verify each candidate page/component/service is not imported anywhere reachable from:

```text
frontend/src/App.tsx
frontend/src/pages/Login.tsx
frontend/src/pages/Register.tsx
frontend/src/pages/ProjectList.tsx
frontend/src/pages/ProjectDetail.tsx
frontend/src/pages/OntologyMap.tsx
frontend/src/pages/Watchlist.tsx
frontend/src/components/Layout/MainLayout.tsx
frontend/src/components/Layout/Sidebar.tsx
```

Then delete the listed unreferenced frontend files exactly. Do not change current routes in `frontend/src/App.tsx` unless removing stale imports becomes necessary.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_frontend_keeps_only_currently_routed_pages_and_supporting_modules -v && cd /Users/wangfushuaiqi/omaha_ontocenter/frontend && npm run build`
Expected: PASS with `1 passed` and a successful Vite build

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_repository_active_surfaces.py
git add -u frontend/src
git commit -m "refactor: remove dead frontend surfaces"
```

### Task 7: Remove dead backend and deployment leftovers outside active paths

**Files:**
- Modify: `deployment/README.md:1-200`
- Delete: `backend/E2E_TEST_REPORT.md`
- Delete: `backend/EXECUTIVE_SUMMARY.md`
- Delete: `backend/FINAL_E2E_TEST_REPORT.md`
- Delete: `backend/ONTOLOGY_CONFIG_ANALYSIS.md`
- Delete: `backend/analyze_e2e_results.py`
- Delete: `backend/revalidate_e2e.py`
- Delete: `backend/test_e2e_ontology.py`
- Delete: `backend/test_focused_e2e.py`
- Delete: `backend/test_phase3_validation.py`
- Delete: `deployment/deploy_part1.sh`
- Delete: `deployment/deploy_to_69.5.23.70.sh`
- Delete: `deployment/web_terminal_deploy.sh`
- Test: `backend/tests/test_repository_active_surfaces.py`

- [ ] **Step 1: Write the failing test**

Add this test to `backend/tests/test_repository_active_surfaces.py`:

```python
def test_backend_and_deployment_leftovers_are_removed():
    root = Path(__file__).resolve().parents[2]

    removed_files = [
        "backend/E2E_TEST_REPORT.md",
        "backend/EXECUTIVE_SUMMARY.md",
        "backend/FINAL_E2E_TEST_REPORT.md",
        "backend/ONTOLOGY_CONFIG_ANALYSIS.md",
        "backend/analyze_e2e_results.py",
        "backend/revalidate_e2e.py",
        "backend/test_e2e_ontology.py",
        "backend/test_focused_e2e.py",
        "backend/test_phase3_validation.py",
        "deployment/deploy_part1.sh",
        "deployment/deploy_to_69.5.23.70.sh",
        "deployment/web_terminal_deploy.sh",
    ]

    present = [path for path in removed_files if (root / path).exists()]
    assert present == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_backend_and_deployment_leftovers_are_removed -v`
Expected: FAIL showing the leftover backend report and deployment files

- [ ] **Step 3: Write minimal implementation**

Delete the listed files exactly. Rewrite `deployment/README.md` so it names only the deployment scripts that remain active after cleanup, with a single preferred deployment path.

Use this surviving deployment set in the document:

```text
deployment/setup_server.sh
deployment/setup_nginx.sh
deployment/setup_cron.sh
deployment/deploy.sh
deployment/backup.sh
deployment/sync_wrapper.sh
deployment/nginx.conf
deployment/omaha-cloud.service
deployment/crontab.txt
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_backend_and_deployment_leftovers_are_removed -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add deployment/README.md backend/tests/test_repository_active_surfaces.py
git add -u backend deployment
git commit -m "chore: remove stale backend and deployment leftovers"
```

### Task 8: Final verification of preserved live/demo capability

**Files:**
- Modify: `backend/tests/test_repository_active_surfaces.py:1-260`
- Test: `backend/app/main.py`
- Test: `backend/app/mcp/server.py`
- Test: `frontend/package.json`

- [ ] **Step 1: Write the failing test**

Add this final smoke-style test to `backend/tests/test_repository_active_surfaces.py`:

```python
def test_repository_root_contains_only_intentional_entrypoints():
    root = Path(__file__).resolve().parents[2]

    allowed_root_entries = {
        ".claude",
        ".env",
        ".env.example",
        ".git",
        ".gitignore",
        ".mcp.json",
        "111.pem",
        "CLAUDE.md",
        "LOCAL_SETUP.md",
        "README.md",
        "RUNNING.md",
        "backend",
        "configs",
        "deployment",
        "docs",
        "frontend",
    }

    actual_entries = {path.name for path in root.iterdir()}
    unexpected = sorted(actual_entries - allowed_root_entries)
    assert unexpected == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_repository_root_contains_only_intentional_entrypoints -v`
Expected: FAIL showing remaining root-level clutter still present

- [ ] **Step 3: Write minimal implementation**

After Tasks 1-7 are complete, delete any remaining unexpected root entries that are not part of the approved active set. Then run the end-to-end verification commands exactly:

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py -v
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && python -c "from app.main import app; print(app.title)"
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && python -c "import app.mcp.server"
cd /Users/wangfushuaiqi/omaha_ontocenter/frontend && npm run build
```

Expected output:
- pytest reports all repository cleanup tests passing
- FastAPI import prints the app title
- MCP server import exits without traceback
- Vite build completes successfully

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && pytest tests/test_repository_active_surfaces.py::test_repository_root_contains_only_intentional_entrypoints -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_repository_active_surfaces.py README.md LOCAL_SETUP.md RUNNING.md deployment/README.md docs/repository-structure.md .gitignore
git add -u .
git commit -m "chore: finalize repository cleanup and structure"
```

---

## Self-Review

### Spec coverage
- Preserve complete live/demo capability: covered by Tasks 1, 6, 7, and 8 verification steps.
- Remove generated artifacts and archive clutter: covered by Task 2.
- Remove one-off tests and temp configs: covered by Task 3.
- Reduce docs to operational guidance: covered by Task 4.
- Remove stale planning/spec/report artifacts: covered by Task 5.
- Normalize root structure and keep only intentional entries: covered by Task 8.

No spec gaps found.

### Placeholder scan
- No `TODO`, `TBD`, or deferred implementation markers remain.
- Each task includes exact file paths and exact commands.
- Risky deletions are preceded by active-surface verification or reference tracing in the task steps.

### Type consistency
- Test file path is consistently `backend/tests/test_repository_active_surfaces.py`.
- Active frontend route set is consistent with `frontend/src/App.tsx`.
- Active deployment set is consistent between Tasks 1, 4, and 7.
