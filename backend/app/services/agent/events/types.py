"""Event type definitions for the agent EventBus."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

TOOL_EXECUTED = "tool.executed"
TOOL_FAILED = "tool.failed"
ONTOLOGY_CONFIRMED = "ontology.confirmed"
DATA_INGESTED = "data.ingested"
SESSION_STARTED = "session.started"


@dataclass
class Event:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
