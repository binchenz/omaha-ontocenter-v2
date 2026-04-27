import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.services.agent.chat_service import ChatService
from app.schemas.chat.agent import AgentChatResponse
from app.services.agent.skills.loader import SkillLoader
import os


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_send_message_delegates_to_agent(db_session):
    service = ChatService(project_id=1, db=db_session)

    mock_response = AgentChatResponse(
        response="订单总额500元",
        data_table=[{"id": 1, "amount": 500}],
        sql="SELECT * FROM t_order",
    )

    with patch("app.services.agent._legacy_chat_service.openai") as mock_openai, \
         patch.object(service, "_load_history", return_value=[]), \
         patch.object(service, "_save_messages"), \
         patch.object(service, "_build_ontology_context", return_value="Product"), \
         patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        mock_response_obj = MagicMock()
        mock_response_obj.choices = [MagicMock()]
        mock_response_obj.choices[0].message.content = "订单总额500元"
        mock_response_obj.choices[0].message.tool_calls = None
        mock_client.chat.completions.create.return_value = mock_response_obj

        result = service.send_message(
            session_id=1,
            user_message="查订单",
            config_yaml="datasources: []",
            llm_provider="openai"
        )

    assert result["message"] == "订单总额500元"


def test_data_query_skill_accepts_wildcards():
    """Verify that data_query skill includes search_* and count_* wildcards."""
    loader = SkillLoader()
    skill = loader.load("data_query")

    assert skill is not None
    assert "search_*" in skill.allowed_tools
    assert "count_*" in skill.allowed_tools
    assert "query_data" in skill.allowed_tools
