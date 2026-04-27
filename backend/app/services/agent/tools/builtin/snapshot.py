"""SnapshotManager + undo_last tool — in-memory snapshot store for undo support."""
from __future__ import annotations

import itertools
from datetime import datetime, timezone
from typing import Any

from app.services.agent.tools.registry import ToolContext, ToolResult, register_tool

# ---------------------------------------------------------------------------
# SnapshotManager
# ---------------------------------------------------------------------------

_id_counter = itertools.count(1)


class SnapshotManager:
    """In-memory snapshot store. Will be migrated to DB later."""

    def __init__(self) -> None:
        self._snapshots: dict[int, list[dict]] = {}

    def take(self, project_id: int, operation: str, data: dict) -> int:
        """Save snapshot before a write operation. Returns snapshot_id."""
        snapshot_id = next(_id_counter)
        snapshot = {
            "id": snapshot_id,
            "operation": operation,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._snapshots.setdefault(project_id, []).append(snapshot)
        return snapshot_id

    def restore_latest(self, project_id: int) -> dict | None:
        """Get the most recent snapshot for a project."""
        snapshots = self._snapshots.get(project_id, [])
        return snapshots[-1] if snapshots else None

    def list_snapshots(self, project_id: int, limit: int = 10) -> list[dict]:
        """List recent snapshots (most recent first)."""
        snapshots = self._snapshots.get(project_id, [])
        return list(reversed(snapshots[-limit:]))


# Global instance
snapshot_manager = SnapshotManager()


# ---------------------------------------------------------------------------
# undo_last tool
# ---------------------------------------------------------------------------

@register_tool(
    name="undo_last",
    description="撤销上一步写操作，恢复到之前的状态。",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def undo_last(params: dict, ctx: ToolContext) -> ToolResult:
    """Restore the most recent snapshot for the current project."""
    project_id = ctx.project_id
    if project_id is None:
        return ToolResult(success=False, error="No project context available")

    snapshot = snapshot_manager.restore_latest(project_id)
    if snapshot is None:
        return ToolResult(success=False, error="没有可撤销的操作")

    return ToolResult(
        success=True,
        data={
            "restored_snapshot_id": snapshot["id"],
            "operation": snapshot["operation"],
            "timestamp": snapshot["timestamp"],
            "data": snapshot["data"],
        },
    )
