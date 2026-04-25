"""Tests for persistent uploaded table behavior in AgentToolkit."""
import os
import tempfile
import pandas as pd
import pytest

from app.services.agent_tools import AgentToolkit
from app.services.uploaded_table_store import UploadedTableStore


@pytest.fixture(autouse=True)
def isolate_uploads(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


def test_in_memory_when_no_session():
    toolkit = AgentToolkit(omaha_service=None)
    assert toolkit.execute_tool("assess_quality", {})["success"] is False


def test_persistent_across_toolkit_instances():
    df = pd.DataFrame({"name": ["a", "a", "b"], "amount": [1, 1, 2]})
    UploadedTableStore.save(project_id=42, session_id=99, table_name="orders", df=df)

    fresh = AgentToolkit(omaha_service=None, project_id=42, session_id=99)
    result = fresh.execute_tool("assess_quality", {})
    assert result["success"] is True
    assert result["data"]["score"] < 100


def test_clean_data_persists_to_store():
    df = pd.DataFrame({"name": [" a ", "b "], "amount": [1, 2]})
    UploadedTableStore.save(project_id=1, session_id=2, table_name="t", df=df)

    toolkit = AgentToolkit(omaha_service=None, project_id=1, session_id=2)
    toolkit.execute_tool("clean_data", {"rules": ["strip_whitespace"]})

    reloaded = UploadedTableStore.load(1, 2, "t")
    assert reloaded["name"].iloc[0] == "a"
    assert reloaded["name"].iloc[1] == "b"
