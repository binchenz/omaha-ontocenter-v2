"""
Unit tests for slug generation and persistence in ontology objects and properties.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.auth.tenant import Tenant
from app.models.ontology.ontology import OntologyObject, ObjectProperty
from app.services.ontology.slug import slugify_name, ensure_unique_slug
from app.services.ontology.store import OntologyStore
from app.services.ontology.importer import OntologyImporter


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


class TestSlugifyName:
    """Test slug generation from names."""

    def test_simple_name(self):
        assert slugify_name("Customer") == "customer"

    def test_name_with_spaces(self):
        assert slugify_name("Customer Order") == "customer-order"

    def test_name_with_underscores(self):
        assert slugify_name("Order_Item") == "order-item"

    def test_name_with_special_chars(self):
        assert slugify_name("ROE %") == "roe"

    def test_name_with_mixed_case(self):
        assert slugify_name("OrderItem") == "orderitem"

    def test_name_with_multiple_spaces(self):
        assert slugify_name("Customer   Order") == "customer-order"

    def test_name_with_leading_trailing_spaces(self):
        assert slugify_name("  Customer Order  ") == "customer-order"

    def test_name_with_numbers(self):
        assert slugify_name("Order 2024") == "order-2024"

    def test_empty_string(self):
        # Empty input returns empty string (no hash — nothing to hash-identify)
        assert slugify_name("") == ""

    def test_only_special_chars(self):
        # Non-empty input that strips to nothing gets a hash fallback
        result = slugify_name("%%%")
        assert result.startswith("obj_")
        assert len(result) == 12  # "obj_" + 8 hex chars

    def test_chinese_name_produces_nonempty_slug(self):
        # Chinese names must produce a non-empty slug (pinyin or hash fallback)
        result = slugify_name("客户订单")
        assert result != ""
        assert result.isascii()


class TestEnsureUniqueSlug:
    """Test slug uniqueness enforcement."""

    def test_unique_slug_no_existing(self, db_session, tenant):
        # No rows exist — base slug returned as-is
        unique_slug = ensure_unique_slug(
            db_session, "customer", "ontology_objects", "slug",
            tenant_id=tenant.id,
        )
        assert unique_slug == "customer"

    def test_unique_slug_with_collision(self, db_session, tenant):
        obj1 = OntologyObject(
            tenant_id=tenant.id,
            name="Customer",
            slug="customer",
            source_entity="t_customer",
            datasource_id="mysql",
            datasource_type="sql",
        )
        db_session.add(obj1)
        db_session.commit()

        unique_slug = ensure_unique_slug(
            db_session, "customer", "ontology_objects", "slug",
            tenant_id=tenant.id,
        )
        assert unique_slug == "customer-1"

    def test_unique_slug_with_multiple_collisions(self, db_session, tenant):
        for slug in ("customer", "customer-1", "customer-2"):
            obj = OntologyObject(
                tenant_id=tenant.id,
                name=slug,
                slug=slug,
                source_entity=f"t_{slug}",
                datasource_id="mysql",
                datasource_type="sql",
            )
            db_session.add(obj)
        db_session.commit()

        unique_slug = ensure_unique_slug(
            db_session, "customer", "ontology_objects", "slug",
            tenant_id=tenant.id,
        )
        assert unique_slug == "customer-3"

    def test_unique_slug_exclude_id(self, db_session, tenant):
        obj = OntologyObject(
            tenant_id=tenant.id,
            name="Customer",
            slug="customer",
            source_entity="t_customer",
            datasource_id="mysql",
            datasource_type="sql",
        )
        db_session.add(obj)
        db_session.commit()

        # Excluding the object's own ID — same slug is available
        unique_slug = ensure_unique_slug(
            db_session, "customer", "ontology_objects", "slug",
            exclude_id=obj.id, tenant_id=tenant.id,
        )
        assert unique_slug == "customer"

    def test_unique_slug_different_tenants_no_collision(self, db_session):
        t1 = Tenant(name="Tenant 1", plan="free")
        t2 = Tenant(name="Tenant 2", plan="free")
        db_session.add_all([t1, t2])
        db_session.commit()

        db_session.add(OntologyObject(
            tenant_id=t1.id, name="Customer", slug="customer",
            source_entity="t_c", datasource_id="db", datasource_type="sql",
        ))
        db_session.commit()

        # Same slug for a different tenant should not collide
        unique_slug = ensure_unique_slug(
            db_session, "customer", "ontology_objects", "slug",
            tenant_id=t2.id,
        )
        assert unique_slug == "customer"


class TestOntologyStoreSlugPersistence:
    """Test slug persistence in OntologyStore."""

    def test_create_object_generates_slug(self, db_session, tenant):
        store = OntologyStore(db_session)
        obj = store.create_object(
            tenant_id=tenant.id,
            name="Customer Order",
            source_entity="t_order",
            datasource_id="mysql",
            datasource_type="sql",
        )
        assert obj.slug == "customer-order"

    def test_create_object_with_explicit_slug(self, db_session, tenant):
        """Explicit slug parameter is ignored - always generated from name for safety."""
        store = OntologyStore(db_session)
        obj = store.create_object(
            tenant_id=tenant.id,
            name="Customer Order",
            slug="custom-slug",  # This will be ignored
            source_entity="t_order",
            datasource_id="mysql",
            datasource_type="sql",
        )
        assert obj.slug == "customer-order"  # Generated from name

    def test_create_object_slug_uniqueness(self, db_session, tenant):
        store = OntologyStore(db_session)
        # "Customer" and "CUSTOMER" both slugify to "customer" — slug must be deduplicated
        obj1 = store.create_object(
            tenant_id=tenant.id,
            name="Customer",
            source_entity="t_customer",
            datasource_id="mysql",
            datasource_type="sql",
        )
        obj2 = store.create_object(
            tenant_id=tenant.id,
            name="CUSTOMER",
            source_entity="t_customer_2",
            datasource_id="mysql",
            datasource_type="sql",
        )
        assert obj1.slug == "customer"
        assert obj2.slug == "customer-1"

    def test_add_property_generates_slug(self, db_session, tenant):
        store = OntologyStore(db_session)
        obj = store.create_object(
            tenant_id=tenant.id,
            name="Customer",
            source_entity="t_customer",
            datasource_id="mysql",
            datasource_type="sql",
        )
        prop = store.add_property(
            object_id=obj.id,
            name="Customer Name",
            data_type="string",
        )
        assert prop.slug == "customer-name"

    def test_add_property_slug_uniqueness_per_object(self, db_session, tenant):
        store = OntologyStore(db_session)
        obj = store.create_object(
            tenant_id=tenant.id,
            name="Customer",
            source_entity="t_customer",
            datasource_id="mysql",
            datasource_type="sql",
        )
        # "Name" and "NAME" both slugify to "name" — slug must be deduplicated
        prop1 = store.add_property(object_id=obj.id, name="Name", data_type="string")
        prop2 = store.add_property(object_id=obj.id, name="NAME", data_type="string")
        assert prop1.slug == "name"
        assert prop2.slug == "name-1"

    def test_rename_object_regenerates_slug(self, db_session, tenant):
        store = OntologyStore(db_session)
        obj = store.create_object(
            tenant_id=tenant.id,
            name="Customer",
            source_entity="t_customer",
            datasource_id="mysql",
            datasource_type="sql",
        )
        assert obj.slug == "customer"
        store.rename_object(tenant.id, "Customer", "Customer Order")
        db_session.refresh(obj)
        assert obj.slug == "customer-order"

    def test_rename_property_regenerates_slug(self, db_session, tenant):
        store = OntologyStore(db_session)
        obj = store.create_object(
            tenant_id=tenant.id,
            name="Customer",
            source_entity="t_customer",
            datasource_id="mysql",
            datasource_type="sql",
        )
        prop = store.add_property(object_id=obj.id, name="Name", data_type="string")
        assert prop.slug == "name"
        store.rename_property(obj.id, "Name", "Full Name")
        db_session.refresh(prop)
        assert prop.slug == "full-name"

    def test_get_full_ontology_includes_slugs(self, db_session, tenant):
        store = OntologyStore(db_session)
        obj = store.create_object(
            tenant_id=tenant.id,
            name="Customer",
            source_entity="t_customer",
            datasource_id="mysql",
            datasource_type="sql",
        )
        store.add_property(object_id=obj.id, name="Customer Name", data_type="string")

        ontology = store.get_full_ontology(tenant.id)
        assert len(ontology["objects"]) == 1
        assert ontology["objects"][0]["slug"] == "customer"
        assert ontology["objects"][0]["properties"][0]["slug"] == "customer-name"


class TestOntologyImporterSlugGeneration:
    """Test slug generation during import."""

    def test_import_generates_object_slugs(self, db_session, tenant):
        importer = OntologyImporter(db_session)
        config = {
            "datasources": [{"id": "mysql", "type": "sql"}],
            "ontology": {
                "objects": [
                    {
                        "name": "Customer Order",
                        "source_entity": "t_order",
                        "datasource": "mysql",
                        "properties": [],
                    }
                ],
                "relationships": [],
            },
        }
        importer.import_dict(tenant.id, config)

        obj = db_session.query(OntologyObject).filter_by(name="Customer Order").first()
        assert obj is not None
        assert obj.slug == "customer-order"

    def test_import_generates_property_slugs(self, db_session, tenant):
        importer = OntologyImporter(db_session)
        config = {
            "datasources": [{"id": "mysql", "type": "sql"}],
            "ontology": {
                "objects": [
                    {
                        "name": "Customer",
                        "source_entity": "t_customer",
                        "datasource": "mysql",
                        "properties": [
                            {"name": "Customer Name", "type": "string"},
                            {"name": "Customer Email", "type": "string"},
                        ],
                    }
                ],
                "relationships": [],
            },
        }
        importer.import_dict(tenant.id, config)

        obj = db_session.query(OntologyObject).filter_by(name="Customer").first()
        props = db_session.query(ObjectProperty).filter_by(object_id=obj.id).order_by(ObjectProperty.id).all()
        assert len(props) == 2
        assert props[0].slug == "customer-name"
        assert props[1].slug == "customer-email"

    def test_import_generates_computed_property_slugs(self, db_session, tenant):
        importer = OntologyImporter(db_session)
        config = {
            "datasources": [{"id": "mysql", "type": "sql"}],
            "ontology": {
                "objects": [
                    {
                        "name": "Stock",
                        "source_entity": "t_stock",
                        "datasource": "mysql",
                        "properties": [],
                        "computed_properties": [
                            {
                                "name": "PE Ratio",
                                "expression": "price / earnings",
                            }
                        ],
                    }
                ],
                "relationships": [],
            },
        }
        importer.import_dict(tenant.id, config)

        obj = db_session.query(OntologyObject).filter_by(name="Stock").first()
        props = db_session.query(ObjectProperty).filter_by(object_id=obj.id).all()
        assert len(props) == 1
        assert props[0].slug == "pe-ratio"
        assert props[0].is_computed is True
