"""
End-to-end test: YAML import → ontology stored in DB → Agent reads ontology → responds.
Validates the full Phase 1 flow works together.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.auth.tenant import Tenant
from app.services.ontology.importer import OntologyImporter
from app.services.ontology.store import OntologyStore
from app.services.agent.toolkit import AgentToolkit
from app.services.agent.react import AgentService
from app.services.legacy.financial.omaha import OmahaService


RETAIL_YAML = """
datasources:
  - id: erp_db
    name: ERP Database
    type: sql
    connection:
      url: "sqlite:///:memory:"

ontology:
  objects:
    - name: Order
      datasource: erp_db
      source_entity: t_order
      description: 客户采购订单
      business_context: 从下单到签收的全生命周期
      domain: retail
      properties:
        - name: id
          type: integer
        - name: customer_name
          type: string
        - name: total_amount
          type: float
          semantic_type: currency_cny
        - name: order_date
          type: date
          semantic_type: date
        - name: status
          type: string
          semantic_type: order_status
      computed_properties:
        - name: avg_item_price
          expression: "{total_amount} / {item_count}"
          semantic_type: currency_cny
    - name: Customer
      datasource: erp_db
      source_entity: t_customer
      description: 客户信息
      domain: retail
      properties:
        - name: id
          type: integer
        - name: name
          type: string
        - name: region
          type: string
          semantic_type: province
  relationships:
    - name: order_customer
      from_object: Order
      to_object: Customer
      type: many_to_one
      join_condition:
        from_field: customer_id
        to_field: id
"""


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_full_phase1_flow(db_session):
    # 1. Create tenant
    tenant = Tenant(name="Retail Corp", plan="free")
    db_session.add(tenant)
    db_session.commit()

    # 2. Import YAML → DB
    importer = OntologyImporter(db_session)
    result = importer.import_yaml(tenant_id=tenant.id, yaml_content=RETAIL_YAML)
    assert result["objects_created"] == 2
    assert result["relationships_created"] == 1

    # 3. Read ontology from DB
    store = OntologyStore(db_session)
    ontology = store.get_full_ontology(tenant_id=tenant.id)
    assert len(ontology["objects"]) == 2
    assert len(ontology["relationships"]) == 1

    order_obj = next(o for o in ontology["objects"] if o["name"] == "Order")
    assert order_obj["domain"] == "retail"
    assert any(p["semantic_type"] == "currency_cny" for p in order_obj["properties"])

    # 4. Build Agent with ontology context
    omaha_service = OmahaService(RETAIL_YAML)
    toolkit = AgentToolkit(omaha_service=omaha_service)
    agent = AgentService(ontology_context=ontology, toolkit=toolkit)

    # 5. Verify system prompt contains business context
    prompt = agent.build_system_prompt()
    assert "客户采购订单" in prompt
    assert "currency_cny" in prompt
    assert "Order" in prompt
    assert "Customer" in prompt

    # 6. Verify tool definitions are available
    tools = toolkit.get_tool_definitions()
    assert len(tools) >= 3
    tool_names = {t["name"] for t in tools}
    assert "query_data" in tool_names
