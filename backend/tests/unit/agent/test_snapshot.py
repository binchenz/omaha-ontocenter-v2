"""Tests for SnapshotManager and undo_last tool."""
from __future__ import annotations

import pytest

from app.services.agent.tools.builtin.snapshot import SnapshotManager, snapshot_manager
from app.services.agent.tools.registry import ToolContext, ToolResult, global_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(project_id: int | None = 1) -> ToolContext:
    return ToolContext(db=None, omaha_service=None, project_id=project_id)


def _fresh_manager() -> SnapshotManager:
    """Return a new SnapshotManager so tests are isolated."""
    return SnapshotManager()


# ---------------------------------------------------------------------------
# SnapshotManager unit tests
# ---------------------------------------------------------------------------

def test_take_and_list():
    mgr = _fresh_manager()
    sid = mgr.take(project_id=1, operation="create_object", data={"name": "Stock"})
    assert isinstance(sid, int)
    snapshots = mgr.list_snapshots(project_id=1)
    assert len(snapshots) == 1
    s = snapshots[0]
    assert s["id"] == sid
    assert s["operation"] == "create_object"
    assert s["data"] == {"name": "Stock"}
    assert "timestamp" in s


def test_restore_latest():
    mgr = _fresh_manager()
    mgr.take(project_id=1, operation="op_first", data={"v": 1})
    sid2 = mgr.take(project_id=1, operation="op_second", data={"v": 2})
    latest = mgr.restore_latest(project_id=1)
    assert latest is not None
    assert latest["id"] == sid2
    assert latest["operation"] == "op_second"


def test_restore_empty():
    mgr = _fresh_manager()
    result = mgr.restore_latest(project_id=99)
    assert result is None


# ---------------------------------------------------------------------------
# undo_last tool tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_undo_last_no_snapshots():
    # Use a project_id that has no snapshots in the global manager
    ctx = _ctx(project_id=999_999)
    result: ToolResult = await global_registry.execute("undo_last", {}, ctx)
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_undo_last_with_snapshot():
    # Seed the global snapshot_manager directly
    snapshot_manager.take(project_id=777, operation="delete_property", data={"prop": "price"})
    ctx = _ctx(project_id=777)
    result: ToolResult = await global_registry.execute("undo_last", {}, ctx)
    assert result.success is True
    assert result.data is not None
    assert result.data["operation"] == "delete_property"
