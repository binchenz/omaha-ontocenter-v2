"""Tests for builtin modeling tools."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from app.services.agent.tools.registry import ToolContext, ToolResult
import app.services.agent.tools.builtin.modeling  # ensure registration


def _ctx(**kwargs) -> ToolContext:
    defaults = dict(db=None, omaha_service=None, project_id=1, session_id=1)
    defaults.update(kwargs)
    return ToolContext(**defaults)


# ---------------------------------------------------------------------------
# scan_tables
# ---------------------------------------------------------------------------

def test_scan_tables_no_data():
    from app.services.agent.tools.registry import global_registry
    ctx = _ctx(uploaded_tables={})
    result = global_registry._handlers["scan_tables"]({}, ctx)
    assert result.success is False
    assert "上传" in result.error


def test_scan_tables_with_data():
    from app.services.agent.tools.registry import global_registry
    df = pd.DataFrame({"col_a": [1, 2, 3], "col_b": ["x", "y", "z"]})
    ctx = _ctx(uploaded_tables={"my_table": df})
    result = global_registry._handlers["scan_tables"]({}, ctx)
    assert result.success is True
    tables = result.data["tables"]
    assert len(tables) == 1
    t = tables[0]
    assert t["name"] == "my_table"
    assert t["row_count"] == 3
    col_names = [c["name"] for c in t["columns"]]
    assert "col_a" in col_names
    assert "col_b" in col_names


# ---------------------------------------------------------------------------
# confirm_ontology — no draft
# ---------------------------------------------------------------------------

def test_confirm_ontology_no_draft():
    from app.services.agent.tools.registry import global_registry

    mock_draft_store = MagicMock()
    mock_draft_store.load.return_value = None

    with patch(
        "app.services.agent.tools.builtin.modeling.OntologyDraftStore",
        mock_draft_store,
        create=True,
    ):
        # We need to patch inside the lazy import path
        with patch(
            "app.services.ontology.draft_store.OntologyDraftStore.load",
            return_value=None,
        ):
            mock_db = MagicMock()
            ctx = _ctx(db=mock_db, project_id=1, session_id=1)
            result = global_registry._handlers["confirm_ontology"]({}, ctx)
            assert result.success is False
            assert "草稿" in result.error
