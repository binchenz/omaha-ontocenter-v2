import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.tenant import Tenant
from app.models.ontology import OntologyObject, ObjectProperty, OntologyRelationship
from app.services.ontology_store import OntologyStore
from app.services.ontology_importer import OntologyImporter


SAMPLE_YAML = """
datasources:
  - id: mysql_erp
    name: ERP Database
    type: sql
    connection:
      url: postgresql://localhost/erp

ontology:
  objects:
    - name: Order
      datasource: mysql_erp
      source_entity: t_order
      description: Customer purchase order
      business_context: Full lifecycle from placement to delivery
      domain: retail
      default_filters:
        - field: status
          operator: "!="
          value: "deleted"
      properties:
        - name: id
          type: integer
          description: Order ID
        - name: total_amount
          type: float
          semantic_type: currency_cny
          description: Order total
        - name: order_date
          type: date
          semantic_type: date
      computed_properties:
        - name: avg_item_price
          expression: "{total_amount} / {item_count}"
          semantic_type: currency_cny
          description: Average price per item
    - name: Customer
      datasource: mysql_erp
      source_entity: t_customer
      description: Customer information
      properties:
        - name: id
          type: integer
        - name: name
          type: string
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


@pytest.fixture
def tenant(db_session):
    t = Tenant(name="Test Corp", plan="free")
    db_session.add(t)
    db_session.commit()
    return t


def test_import_yaml_creates_objects(db_session, tenant):
    importer = OntologyImporter(db_session)
    result = importer.import_yaml(tenant_id=tenant.id, yaml_content=SAMPLE_YAML)
    assert result["objects_created"] == 2
    assert result["relationships_created"] == 1


def test_import_yaml_properties(db_session, tenant):
    importer = OntologyImporter(db_session)
    importer.import_yaml(tenant_id=tenant.id, yaml_content=SAMPLE_YAML)
    store = OntologyStore(db_session)
    order = store.get_object(tenant_id=tenant.id, name="Order")
    assert order is not None
    prop_names = {p.name for p in order.properties}
    assert "total_amount" in prop_names
    assert "avg_item_price" in prop_names
    computed = [p for p in order.properties if p.is_computed]
    assert len(computed) == 1
    assert computed[0].expression == "{total_amount} / {item_count}"


def test_import_yaml_default_filters(db_session, tenant):
    importer = OntologyImporter(db_session)
    importer.import_yaml(tenant_id=tenant.id, yaml_content=SAMPLE_YAML)
    store = OntologyStore(db_session)
    order = store.get_object(tenant_id=tenant.id, name="Order")
    assert order.default_filters == [{"field": "status", "operator": "!=", "value": "deleted"}]


def test_import_yaml_relationships(db_session, tenant):
    importer = OntologyImporter(db_session)
    importer.import_yaml(tenant_id=tenant.id, yaml_content=SAMPLE_YAML)
    rels = db_session.query(OntologyRelationship).filter_by(tenant_id=tenant.id).all()
    assert len(rels) == 1
    assert rels[0].name == "order_customer"
    assert rels[0].from_field == "customer_id"


def test_import_yaml_source_entity_fallback(db_session, tenant):
    """If source_entity not present, fall back to api_name for backward compat."""
    yaml_with_api_name = """
datasources:
  - id: tushare_pro
    type: tushare
    connection:
      token: test
ontology:
  objects:
    - name: Stock
      datasource: tushare_pro
      api_name: stock_basic
      properties:
        - name: ts_code
          type: string
"""
    importer = OntologyImporter(db_session)
    importer.import_yaml(tenant_id=tenant.id, yaml_content=yaml_with_api_name)
    store = OntologyStore(db_session)
    stock = store.get_object(tenant_id=tenant.id, name="Stock")
    assert stock.source_entity == "stock_basic"
