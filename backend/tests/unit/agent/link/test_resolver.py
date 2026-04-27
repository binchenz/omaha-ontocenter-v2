import pytest
from app.services.agent.link import LinkResolver, LinkDefinition


@pytest.fixture
def sample_ontology():
    return {
        "objects": [
            {
                "name": "Order",
                "slug": "order",
                "datasource_type": "postgresql",
                "datasource_id": "main_db",
                "properties": [
                    {"name": "id", "slug": "id", "type": "string"},
                    {
                        "name": "customer",
                        "slug": "customer",
                        "type": "link",
                        "link_target": "Customer",
                        "link_foreign_key": "customer_id",
                        "link_target_key": "id",
                    },
                ],
            },
            {
                "name": "Customer",
                "slug": "customer",
                "datasource_type": "postgresql",
                "datasource_id": "main_db",
                "properties": [
                    {"name": "id", "slug": "id", "type": "string"},
                    {"name": "name", "slug": "name", "type": "string"},
                ],
            },
        ]
    }


def test_resolve_link(sample_ontology):
    result = LinkResolver.resolve_link("Order", "customer", sample_ontology)

    assert result is not None
    assert isinstance(result, LinkDefinition)
    assert result.source_object == "Order"
    assert result.source_slug == "order"
    assert result.link_field == "customer"
    assert result.target_object == "Customer"
    assert result.target_slug == "customer"
    assert result.foreign_key == "customer_id"
    assert result.target_key == "id"
    assert result.datasource_type == "postgresql"
    assert result.datasource_id == "main_db"


def test_resolve_non_link_field(sample_ontology):
    result = LinkResolver.resolve_link("Order", "id", sample_ontology)
    assert result is None


def test_resolve_nonexistent_object(sample_ontology):
    result = LinkResolver.resolve_link("NonExistent", "customer", sample_ontology)
    assert result is None


def test_resolve_nonexistent_field(sample_ontology):
    result = LinkResolver.resolve_link("Order", "nonexistent", sample_ontology)
    assert result is None
