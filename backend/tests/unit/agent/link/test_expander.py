import pytest
from unittest.mock import Mock
from app.services.agent.link import LinkExpander


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
                    {"name": "customer_id", "slug": "customer_id", "type": "string"},
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


@pytest.fixture
def mock_ctx():
    ctx = Mock()
    ctx.config_yaml = "mock_config"
    ctx.omaha_service = Mock()
    return ctx


def test_expand_links(sample_ontology, mock_ctx):
    rows = [
        {"id": "order1", "customer_id": "cust1"},
        {"id": "order2", "customer_id": "cust2"},
    ]

    mock_ctx.omaha_service.query_objects.side_effect = [
        {"success": True, "data": [{"id": "cust1", "name": "Alice"}]},
        {"success": True, "data": [{"id": "cust2", "name": "Bob"}]},
    ]

    result = LinkExpander.expand_links(rows, "Order", sample_ontology, mock_ctx)

    assert len(result) == 2
    assert result[0]["customer"] == {"id": "cust1", "name": "Alice"}
    assert result[1]["customer"] == {"id": "cust2", "name": "Bob"}
    assert mock_ctx.omaha_service.query_objects.call_count == 2


def test_expand_links_empty_rows(sample_ontology, mock_ctx):
    result = LinkExpander.expand_links([], "Order", sample_ontology, mock_ctx)
    assert result == []
    mock_ctx.omaha_service.query_objects.assert_not_called()


def test_expand_links_no_link_fields(sample_ontology, mock_ctx):
    rows = [{"id": "cust1", "name": "Alice"}]
    result = LinkExpander.expand_links(rows, "Customer", sample_ontology, mock_ctx)
    assert result == rows
    mock_ctx.omaha_service.query_objects.assert_not_called()
