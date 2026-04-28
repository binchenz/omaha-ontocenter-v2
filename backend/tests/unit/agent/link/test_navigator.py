import pytest
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from unittest.mock import Mock
from app.services.agent.link.navigator import PathNavigator


@pytest.fixture
def retail_ontology():
    return {
        "objects": [
            {
                "name": "Category",
                "slug": "category",
                "datasource_type": "postgresql",
                "datasource_id": "main_db",
                "properties": [
                    {"name": "id", "slug": "id", "type": "string"},
                    {"name": "name", "slug": "name", "type": "string"},
                ],
            },
            {
                "name": "SKU",
                "slug": "sku",
                "datasource_type": "postgresql",
                "datasource_id": "main_db",
                "properties": [
                    {"name": "id", "slug": "id", "type": "string"},
                    {"name": "name", "slug": "name", "type": "string"},
                    {"name": "category_id", "slug": "category_id", "type": "string"},
                    {
                        "name": "category",
                        "slug": "category",
                        "type": "link",
                        "link": {
                            "target": "Category",
                            "foreign_key": "category_id",
                            "target_key": "id",
                        }
                    },
                ],
            },
            {
                "name": "Review",
                "slug": "review",
                "datasource_type": "postgresql",
                "datasource_id": "main_db",
                "properties": [
                    {"name": "id", "slug": "id", "type": "string"},
                    {"name": "content", "slug": "content", "type": "string"},
                    {"name": "sku_id", "slug": "sku_id", "type": "string"},
                    {
                        "name": "sku",
                        "slug": "sku",
                        "type": "link",
                        "link": {
                            "target": "SKU",
                            "foreign_key": "sku_id",
                            "target_key": "id",
                        }
                    },
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


def test_navigate_single_hop(retail_ontology, mock_ctx):
    params = {
        "start_object": "SKU",
        "start_filters": {"id": "sku1"},
        "path": ["category"],
        "fields": ["id", "name"],
    }

    mock_ctx.omaha_service.query_objects.side_effect = [
        {"success": True, "data": [{"id": "sku1", "name": "Phone", "category_id": "cat1"}]},
        {"success": True, "data": [{"id": "cat1", "name": "Electronics"}]},
    ]

    result = PathNavigator.navigate(params, retail_ontology, mock_ctx)

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["id"] == "cat1"
    assert result["data"][0]["name"] == "Electronics"
    assert mock_ctx.omaha_service.query_objects.call_count == 2


def test_navigate_multi_hop(retail_ontology, mock_ctx):
    params = {
        "start_object": "Review",
        "start_filters": {"id": "rev1"},
        "path": ["sku", "category"],
        "fields": ["id", "name"],
    }

    mock_ctx.omaha_service.query_objects.side_effect = [
        {"success": True, "data": [{"id": "rev1", "content": "Great!", "sku_id": "sku1"}]},
        {"success": True, "data": [{"id": "sku1", "name": "Phone", "category_id": "cat1"}]},
        {"success": True, "data": [{"id": "cat1", "name": "Electronics"}]},
    ]

    result = PathNavigator.navigate(params, retail_ontology, mock_ctx)

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["id"] == "cat1"
    assert result["data"][0]["name"] == "Electronics"
    assert mock_ctx.omaha_service.query_objects.call_count == 3

