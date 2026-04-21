from pathlib import Path
import subprocess


def _path_exists_in_head(root: Path, relative_path: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"HEAD:{relative_path}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _root_entries_in_head(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "--name-only", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    entries = {line for line in result.stdout.splitlines() if line}
    if (root / ".git").exists():
        entries.add(".git")
    if (root / ".env").exists():
        entries.add(".env")
    return entries


def test_current_active_surfaces_are_documented():
    repo_root = Path(__file__).resolve().parents[2]

    required_files = [
        "backend/app/main.py",
        "backend/app/api/__init__.py",
        "backend/app/mcp/server.py",
        "frontend/src/App.tsx",
        "frontend/src/components/Layout/Sidebar.tsx",
        "deployment/README.md",
        "configs/financial_stock_analysis.yaml",
    ]

    for file_path in required_files:
        assert _path_exists_in_head(repo_root, file_path), f"Required file not found: {file_path}"


def test_repository_root_excludes_generated_and_archive_clutter():
    repo_root = Path(__file__).resolve().parents[2]

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

    for path in disallowed_paths:
        assert not _path_exists_in_head(repo_root, path), f"Disallowed path found: {path}"


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

    for path in disallowed_paths:
        assert not _path_exists_in_head(root, path), f"Disallowed root-level file found: {path}"


def test_docs_are_reduced_to_current_operational_materials():
    root = Path(__file__).resolve().parents[2]

    required_files = [
        "README.md",
        "LOCAL_SETUP.md",
        "RUNNING.md",
        "deployment/README.md",
        "docs/repository-structure.md",
    ]

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

    for file_path in required_files:
        assert _path_exists_in_head(root, file_path), f"Required file not found: {file_path}"

    for file_path in removed_files:
        assert not _path_exists_in_head(root, file_path), f"File should have been removed: {file_path}"


def test_only_current_design_references_remain_under_docs_superpowers():
    root = Path(__file__).resolve().parents[2]

    required_files = [
        "docs/superpowers/specs/2026-04-21-repo-cleanup-design.md",
        "docs/superpowers/specs/2026-03-29-ontology-map-design.md",
        "docs/superpowers/specs/2026-04-12-university-talk-design.md",
        "docs/superpowers/plans/2026-03-29-ontology-map-plan.md",
        "docs/superpowers/plans/2026-04-12-university-talk.md",
    ]

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

    for file_path in required_files:
        assert _path_exists_in_head(root, file_path), f"Required file not found: {file_path}"

    for file_path in removed_files:
        assert not _path_exists_in_head(root, file_path), f"File should have been removed: {file_path}"


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

    for file_path in removed_files:
        assert not _path_exists_in_head(root, file_path), f"File should have been removed: {file_path}"


def test_repository_root_contains_only_intentional_entrypoints():
    root = Path(__file__).resolve().parents[2]

    allowed_root_entries = {
        ".claude",
        ".env",
        ".env.example",
        ".git",
        ".gitignore",
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

    actual_entries = _root_entries_in_head(root)
    unexpected = sorted(actual_entries - allowed_root_entries)
    assert unexpected == []


def test_frontend_dead_surfaces_are_removed():
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

    removed_files = [
        "frontend/src/pages/AssetList.tsx",
        "frontend/src/pages/OntologyViewer.tsx",
        "frontend/src/components/LineageGraph.tsx",
        "frontend/src/pages/SemanticEditor.tsx",
        "frontend/src/components/semantic/AgentPreview.tsx",
        "frontend/src/components/semantic/FormulaBuilder.tsx",
        "frontend/src/components/semantic/ObjectList.tsx",
        "frontend/src/components/semantic/PropertyEditor.tsx",
    ]

    for file_path in required_files:
        assert _path_exists_in_head(root, file_path), f"Required file not found: {file_path}"

    for file_path in removed_files:
        assert not _path_exists_in_head(root, file_path), f"File should have been removed: {file_path}"


def test_backend_requirements_pin_locally_verified_runtime_versions():
    root = Path(__file__).resolve().parents[2]
    requirements = (root / "backend" / "requirements.txt").read_text(encoding="utf-8")

    assert "fastapi==0.135.1" in requirements
    assert "uvicorn[standard]==0.41.0" in requirements
    assert "sqlalchemy==2.0.48" in requirements
    assert "pydantic==2.12.5" in requirements
    assert "pydantic-settings==2.13.1" in requirements
    assert "python-jose[cryptography]==3.5.0" in requirements
    assert "python-multipart==0.0.22" in requirements
    assert "pyyaml==6.0.3" in requirements
    assert "httpx==0.28.1" in requirements
    assert "pytest==9.0.2" in requirements
    assert "mcp==1.26.0" in requirements
    assert "email-validator==2.3.0" in requirements
    assert "PyMySQL==1.1.2" in requirements

    assert "fastapi==0.109.0" not in requirements
    assert "uvicorn[standard]==0.27.0" not in requirements
    assert "sqlalchemy==2.0.25" not in requirements
    assert "pydantic==2.5.3" not in requirements
    assert "pydantic-settings==2.1.0" not in requirements
    assert "python-jose[cryptography]==3.3.0" not in requirements
    assert "httpx==0.26.0" not in requirements
    assert "python-multipart==0.0.6" not in requirements
    assert "pyyaml==6.0.1" not in requirements
    assert "pytest==7.4.4" not in requirements
    assert "mcp>=1.0.0" not in requirements
