import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.services.agent.chat_service import ChatService
from app.schemas.agent import AgentChatResponse


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

    with patch("app.services.chat.AgentService") as MockAgent, \
         patch.object(service, "_load_history", return_value=[]), \
         patch.object(service, "_save_messages"):
        MockAgent.return_value.chat.return_value = mock_response
        result = service.send_message(
            session_id=1,
            user_message="查订单",
            config_yaml="datasources: []",
        )

    assert result["message"] == "订单总额500元"
    assert result["data_table"] == [{"id": 1, "amount": 500}]
    assert result["sql"] == "SELECT * FROM t_order"
