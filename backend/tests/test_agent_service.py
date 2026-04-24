import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.tenant import Tenant
from app.services.ontology_store import OntologyStore
from app.agents.agent_service import AgentService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def tenant(db_session):
    t = Tenant(name="Test Corp", plan="free")
    db_session.add(t)
    db_session.commit()
    return t


@pytest.fixture
def populated_store(db_session, tenant):
    store = OntologyStore(db_session)
    obj = store.create_object(
        tenant_id=tenant.id, name="Order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
        description="Customer purchase order",
    )
    store.add_property(object_id=obj.id, name="total_amount", data_type="float", semantic_type="currency_cny")
    store.add_property(object_id=obj.id, name="status", data_type="string", semantic_type="order_status")
    return tenant


def test_agent_context_contains_object_info(db_session, populated_store):
    agent = AgentService(db_session, tenant_id=populated_store.id)
    context = agent.get_agent_context()
    assert "Order" in context
    assert "total_amount" in context


def test_agent_run_query_order(db_session, populated_store):
    agent = AgentService(db_session, tenant_id=populated_store.id)
    result = agent.run("Query all Orders")
    assert "Order" in result["response"]
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["tool"] == "query_ontology_object"


def test_agent_run_schema_request(db_session, populated_store):
    agent = AgentService(db_session, tenant_id=populated_store.id)
    result = agent.run("What is the schema of Order?")
    assert result["tool_calls"][0]["tool"] == "get_ontology_schema"


def test_agent_run_no_matching_object(db_session, tenant):
    agent = AgentService(db_session, tenant_id=tenant.id)
    result = agent.run("Show me Products")
    assert "not sure" in result["response"].lower() or "specify" in result["response"].lower()
