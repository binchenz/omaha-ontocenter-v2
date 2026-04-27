"""Tests for ChatServiceV2 (thin chat service)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agent.chat_service import ChatServiceV2
from app.services.agent.orchestrator.executor import AgentResponse


def _make_project(setup_stage: str = "ready") -> MagicMock:
    project = MagicMock()
    project.id = 1
    project.tenant_id = 10
    project.owner_id = 10
    project.setup_stage = setup_stage
    return project


def _make_db() -> MagicMock:
    return MagicMock()


@pytest.mark.asyncio
async def test_send_message_simple_query():
    """Mock provider returns text → verify response dict format."""
    project = _make_project(setup_stage="ready")
    db = _make_db()

    mock_response = AgentResponse(
        message="Here are the results.",
        data_table=[{"col": "val"}],
        chart_config=None,
        sql="SELECT 1",
        structured=None,
        setup_stage=None,
    )

    with (
        patch(
            "app.services.agent.chat_service.ProviderFactory.create",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.agent.chat_service.SessionManager.load_history",
            return_value=[],
        ),
        patch(
            "app.services.agent.chat_service.OntologyStore",
        ) as MockStore,
        patch(
            "app.services.agent.chat_service.ExecutorAgent.run",
            new_callable=AsyncMock,
            return_value=mock_response,
        ),
    ):
        MockStore.return_value.get_full_ontology.return_value = {"objects": []}

        svc = ChatServiceV2(project=project, db=db)
        result = await svc.send_message(session_id=1, user_message="show me data")

    assert "message" in result
    assert "setup_stage" in result
    assert "data_table" in result
    assert result["message"] == "Here are the results."
    assert result["data_table"] == [{"col": "val"}]


@pytest.mark.asyncio
async def test_send_message_with_tool_call():
    """Mock provider returns tool call then text → verify tool was executed."""
    project = _make_project(setup_stage="ready")
    db = _make_db()

    mock_response = AgentResponse(
        message="Query complete.",
        data_table=[{"stock": "AAPL", "price": 150}],
        chart_config={"type": "bar"},
        sql="SELECT * FROM stocks",
        structured=None,
        tool_calls=[{"name": "query_data", "params": {}, "result_summary": "ok"}],
    )

    with (
        patch(
            "app.services.agent.chat_service.ProviderFactory.create",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.agent.chat_service.SessionManager.load_history",
            return_value=[{"role": "user", "content": "prev"}],
        ),
        patch(
            "app.services.agent.chat_service.OntologyStore",
        ) as MockStore,
        patch(
            "app.services.agent.chat_service.ExecutorAgent.run",
            new_callable=AsyncMock,
            return_value=mock_response,
        ),
    ):
        MockStore.return_value.get_full_ontology.return_value = {
            "objects": [{"name": "Stock", "description": "A stock", "properties": []}]
        }

        svc = ChatServiceV2(project=project, db=db)
        result = await svc.send_message(session_id=2, user_message="show me stocks")

    assert result["message"] == "Query complete."
    assert result["data_table"] == [{"stock": "AAPL", "price": 150}]
    assert result["chart_config"] == {"type": "bar"}
    assert result["sql"] == "SELECT * FROM stocks"
