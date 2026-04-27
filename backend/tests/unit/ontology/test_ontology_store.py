import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.auth.tenant import Tenant
from app.models.ontology.ontology import (
    OntologyObject,
    ObjectProperty,
    OntologyRelationship,
    HealthRule,
    BusinessGoal,
    DomainKnowledge,
)


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


def test_create_ontology_object(db_session, tenant):
    obj = OntologyObject(
        tenant_id=tenant.id,
        name="Order",
        slug="order",
        source_entity="t_order",
        datasource_id="mysql_erp",
        datasource_type="sql",
        description="Customer purchase order",
        business_context="Full lifecycle from placement to delivery",
        domain="retail",
    )
    db_session.add(obj)
    db_session.commit()
    assert obj.id is not None
    assert obj.name == "Order"
    assert obj.source_entity == "t_order"


def test_create_object_property(db_session, tenant):
    obj = OntologyObject(
        tenant_id=tenant.id,
        name="Order",
        slug="order",
        source_entity="t_order",
        datasource_id="mysql_erp",
        datasource_type="sql",
    )
    db_session.add(obj)
    db_session.commit()

    prop = ObjectProperty(
        object_id=obj.id,
        name="total_amount",
        slug="total_amount",
        data_type="float",
        semantic_type="currency_cny",
        description="Order total amount",
    )
    db_session.add(prop)
    db_session.commit()
    assert prop.id is not None
    assert prop.semantic_type == "currency_cny"


def test_create_health_rule(db_session, tenant):
    obj = OntologyObject(
        tenant_id=tenant.id,
        name="Order",
        slug="order",
        source_entity="t_order",
        datasource_id="mysql_erp",
        datasource_type="sql",
    )
    db_session.add(obj)
    db_session.commit()

    rule = HealthRule(
        object_id=obj.id,
        metric="avg_delivery_days",
        expression="avg(delivery_date - order_date)",
        warning_threshold="> 3",
        critical_threshold="> 7",
        advice="Check warehouse capacity",
    )
    db_session.add(rule)
    db_session.commit()
    assert rule.id is not None


def test_create_relationship(db_session, tenant):
    order = OntologyObject(
        tenant_id=tenant.id, name="Order", slug="order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
    )
    customer = OntologyObject(
        tenant_id=tenant.id, name="Customer", slug="customer",
        source_entity="t_customer", datasource_id="mysql_erp", datasource_type="sql",
    )
    db_session.add_all([order, customer])
    db_session.commit()

    rel = OntologyRelationship(
        tenant_id=tenant.id,
        name="order_customer",
        from_object_id=order.id,
        to_object_id=customer.id,
        relationship_type="many_to_one",
        from_field="customer_id",
        to_field="id",
    )
    db_session.add(rel)
    db_session.commit()
    assert rel.id is not None


from app.services.ontology.store import OntologyStore


def test_store_create_object(db_session, tenant):
    store = OntologyStore(db_session)
    obj = store.create_object(
        tenant_id=tenant.id,
        name="Product",
        source_entity="t_product",
        datasource_id="mysql_erp",
        datasource_type="sql",
        description="Product catalog",
        domain="retail",
    )
    assert obj.id is not None
    assert obj.name == "Product"


def test_store_list_objects(db_session, tenant):
    store = OntologyStore(db_session)
    store.create_object(
        tenant_id=tenant.id, name="Product",
        source_entity="t_product", datasource_id="mysql_erp", datasource_type="sql",
    )
    store.create_object(
        tenant_id=tenant.id, name="Order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
    )
    objects = store.list_objects(tenant_id=tenant.id)
    assert len(objects) == 2


def test_store_get_object_with_properties(db_session, tenant):
    store = OntologyStore(db_session)
    obj = store.create_object(
        tenant_id=tenant.id, name="Product",
        source_entity="t_product", datasource_id="mysql_erp", datasource_type="sql",
    )
    store.add_property(
        object_id=obj.id, name="price", data_type="float", semantic_type="currency_cny",
    )
    store.add_property(
        object_id=obj.id, name="name", data_type="string", semantic_type="text",
    )
    result = store.get_object(tenant_id=tenant.id, name="Product")
    assert result is not None
    assert len(result.properties) == 2


def test_store_add_health_rule(db_session, tenant):
    store = OntologyStore(db_session)
    obj = store.create_object(
        tenant_id=tenant.id, name="Order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
    )
    rule = store.add_health_rule(
        object_id=obj.id,
        metric="avg_delivery_days",
        expression="avg(delivery_date - order_date)",
        warning_threshold="> 3",
        critical_threshold="> 7",
        advice="Check warehouse capacity",
    )
    assert rule.id is not None
    refreshed = store.get_object(tenant_id=tenant.id, name="Order")
    assert len(refreshed.health_rules) == 1


def test_store_tenant_isolation(db_session):
    store = OntologyStore(db_session)
    t1 = Tenant(name="Corp A", plan="free")
    t2 = Tenant(name="Corp B", plan="free")
    db_session.add_all([t1, t2])
    db_session.commit()

    store.create_object(
        tenant_id=t1.id, name="Product",
        source_entity="t_product", datasource_id="db1", datasource_type="sql",
    )
    store.create_object(
        tenant_id=t2.id, name="Product",
        source_entity="t_product", datasource_id="db2", datasource_type="sql",
    )
    assert len(store.list_objects(tenant_id=t1.id)) == 1
    assert len(store.list_objects(tenant_id=t2.id)) == 1
    assert store.get_object(tenant_id=t1.id, name="Product").datasource_id == "db1"


def test_store_delete_object_cascades(db_session, tenant):
    store = OntologyStore(db_session)
    obj = store.create_object(
        tenant_id=tenant.id, name="Order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
    )
    store.add_property(object_id=obj.id, name="amount", data_type="float")
    store.add_health_rule(
        object_id=obj.id, metric="total", expression="sum(amount)",
    )
    store.delete_object(tenant_id=tenant.id, name="Order")
    assert store.get_object(tenant_id=tenant.id, name="Order") is None


def test_add_link_property(db_session, tenant):
    store = OntologyStore(db_session)
    order = store.create_object(
        tenant_id=tenant.id, name="Order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
    )
    customer = store.create_object(
        tenant_id=tenant.id, name="Customer",
        source_entity="t_customer", datasource_id="mysql_erp", datasource_type="sql",
    )

    link_prop = store.add_property(
        object_id=order.id,
        name="customer",
        data_type="link",
        link_target="Customer",
        link_foreign_key="customer_id",
        link_target_key="id",
    )

    assert link_prop.data_type == "link"
    assert link_prop.link_target_id == customer.id
    assert link_prop.link_foreign_key == "customer_id"
    assert link_prop.link_target_key == "id"


def test_add_self_referencing_link(db_session, tenant):
    store = OntologyStore(db_session)
    category = store.create_object(
        tenant_id=tenant.id, name="Category",
        source_entity="t_category", datasource_id="mysql_erp", datasource_type="sql",
    )

    link_prop = store.add_property(
        object_id=category.id,
        name="parent",
        data_type="link",
        link_target="Category",
        link_foreign_key="parent_id",
    )

    assert link_prop.data_type == "link"
    assert link_prop.link_target_id == category.id
    assert link_prop.link_foreign_key == "parent_id"
    assert link_prop.link_target_key == "id"


def test_add_link_property_missing_target(db_session, tenant):
    store = OntologyStore(db_session)
    order = store.create_object(
        tenant_id=tenant.id, name="Order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
    )

    with pytest.raises(ValueError, match="Link type requires link_target"):
        store.add_property(
            object_id=order.id,
            name="customer",
            data_type="link",
            link_foreign_key="customer_id",
        )


def test_add_link_property_missing_foreign_key(db_session, tenant):
    store = OntologyStore(db_session)
    order = store.create_object(
        tenant_id=tenant.id, name="Order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
    )

    with pytest.raises(ValueError, match="Link type requires link_foreign_key"):
        store.add_property(
            object_id=order.id,
            name="customer",
            data_type="link",
            link_target="Customer",
        )


def test_add_link_property_target_not_found(db_session, tenant):
    store = OntologyStore(db_session)
    order = store.create_object(
        tenant_id=tenant.id, name="Order",
        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql",
    )

    with pytest.raises(ValueError, match="Target object 'Customer' not found"):
        store.add_property(
            object_id=order.id,
            name="customer",
            data_type="link",
            link_target="Customer",
            link_foreign_key="customer_id",
        )
