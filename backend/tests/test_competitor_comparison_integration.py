"""
Integration tests for CompetitorComparison object.

Tests the new CompetitorComparison object through MCP tools.
"""
import pytest
from pathlib import Path
from app.mcp.tools import list_objects, get_schema, query_data


# Load ontology config
CONFIG_PATH = Path(__file__).parent.parent.parent / "docs/superpowers/ontology_redesign_v2.yaml"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG_YAML = f.read()


class TestCompetitorComparisonBasic:
    """Test basic CompetitorComparison queries."""

    def test_list_objects_includes_competitor_comparison(self):
        """Verify CompetitorComparison is in object list."""
        result = list_objects(CONFIG_YAML)

        assert result["success"] is True
        object_names = [obj["name"] for obj in result["objects"]]
        assert "CompetitorComparison" in object_names

        # Find CompetitorComparison object
        comp_obj = next(obj for obj in result["objects"] if obj["name"] == "CompetitorComparison")
        assert "竞品价格对比专用对象" in comp_obj["description"]

    def test_get_competitor_comparison_schema(self):
        """Verify CompetitorComparison schema includes minimal identification set."""
        result = get_schema(CONFIG_YAML, "CompetitorComparison")

        assert result["success"] is True
        assert result["object_type"] == "CompetitorComparison"

        # Check minimal identification set (columns key, not properties)
        column_names = [c["name"] for c in result.get("columns", [])]
        assert "sku_name" in column_names
        assert "city" in column_names
        assert "product_type_first_level" in column_names

        # Check detailed info NOT included
        assert "product_name" not in column_names
        assert "specification" not in column_names
        assert "brand_name" not in column_names

        # Check computed properties exist
        assert "effective_ppy_price" in column_names or "actual_price_gap" in column_names

    def test_query_competitor_comparison_basic(self):
        """Test basic query returns data with sku_name."""
        result = query_data(
            config_yaml=CONFIG_YAML,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.sku_name",
                "CompetitorComparison.city",
                "CompetitorComparison.platform_id",
                "CompetitorComparison.ppy_price",
                "CompetitorComparison.mall_price"
            ],
            filters=[],
            limit=10
        )

        # Print error if failed
        if not result.get("success"):
            print(f"Query failed: {result.get('error')}")

        assert result["success"] is True, f"Query failed: {result.get('error')}"
        assert len(result["data"]) > 0

        # Check first row has required fields
        first_row = result["data"][0]
        assert "sku_name" in first_row
        assert "city" in first_row
        assert "platform_id" in first_row
        assert first_row["platform_id"]  # Should not be empty (auto-filtered)

    def test_auto_filter_platform_id(self):
        """Verify platform_id IS NOT NULL filter is auto-applied."""
        result = query_data(
            config_yaml=CONFIG_YAML,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.platform_id"
            ],
            filters=[],
            limit=100
        )

        assert result["success"] is True
        # All records should have non-empty platform_id
        for row in result["data"]:
            assert row["platform_id"] is not None
            assert row["platform_id"] != ""


class TestCompetitorComparisonComputedProperties:
    """Test computed properties in CompetitorComparison."""

    def test_actual_price_gap(self):
        """Test actual_price_gap computed property."""
        result = query_data(
            config_yaml=CONFIG_YAML,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.sku_name",
                "CompetitorComparison.ppy_price",
                "CompetitorComparison.mall_price",
                "CompetitorComparison.actual_price_gap"
            ],
            filters=[],
            limit=10
        )

        assert result["success"] is True
        assert len(result["data"]) > 0

        for row in result["data"]:
            # actual_price_gap = ppy_price - mall_price
            expected_gap = float(row["ppy_price"]) - float(row["mall_price"])
            actual_gap = float(row["actual_price_gap"])
            assert abs(actual_gap - expected_gap) < 0.01, \
                f"Expected gap {expected_gap}, got {actual_gap}"

    def test_is_price_advantage(self):
        """Test is_price_advantage boolean computed property."""
        result = query_data(
            config_yaml=CONFIG_YAML,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.sku_name",
                "CompetitorComparison.price_advantage_flag",
                "CompetitorComparison.is_price_advantage"
            ],
            filters=[],
            limit=20
        )

        assert result["success"] is True
        assert len(result["data"]) > 0

        for row in result["data"]:
            # is_price_advantage = 1 if flag=1, else 0
            if row["price_advantage_flag"] == 1:
                assert row["is_price_advantage"] == 1
            else:
                assert row["is_price_advantage"] == 0


class TestCompetitorComparisonAggregation:
    """Test aggregation queries on CompetitorComparison."""

    def test_count_by_city(self):
        """Test counting competitor records by city."""
        result = query_data(
            config_yaml=CONFIG_YAML,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.city",
                "COUNT(*) as total_records"
            ],
            filters=[],
            limit=20
        )

        assert result["success"] is True
        assert len(result["data"]) > 0

        # Should have multiple cities
        cities = [row["city"] for row in result["data"]]
        assert len(set(cities)) > 1

    def test_advantage_rate_by_platform(self):
        """Test calculating price advantage rate by platform."""
        result = query_data(
            config_yaml=CONFIG_YAML,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.platform_id",
                "COUNT(*) as total",
                "SUM(CompetitorComparison.is_price_advantage) as advantage_count"
            ],
            filters=[],
            limit=20
        )

        assert result["success"] is True
        assert len(result["data"]) > 0

        for row in result["data"]:
            assert row["total"] > 0
            assert row["advantage_count"] >= 0
            assert row["advantage_count"] <= row["total"]


class TestCompetitorComparisonChatScenarios:
    """Test real-world chat scenarios using CompetitorComparison."""

    def test_which_products_more_expensive(self):
        """Scenario: 哪些商品比竞品贵？"""
        result = query_data(
            config_yaml=CONFIG_YAML,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.sku_name",
                "CompetitorComparison.city",
                "CompetitorComparison.ppy_price",
                "CompetitorComparison.mall_price",
                "CompetitorComparison.actual_price_gap"
            ],
            filters=[
                {"field": "CompetitorComparison.price_advantage_flag", "operator": "=", "value": 2}
            ],
            limit=10
        )

        assert result["success"] is True
        assert len(result["data"]) > 0

        # All should have sku_name (no need to JOIN)
        for row in result["data"]:
            assert row["sku_name"]
            assert float(row["ppy_price"]) > float(row["mall_price"])

    def test_shenzhen_price_disadvantage(self):
        """Scenario: 深圳站有多少商品价格劣势？"""
        result = query_data(
            config_yaml=CONFIG_YAML,
            object_type="CompetitorComparison",
            selected_columns=[
                "COUNT(DISTINCT CompetitorComparison.sku_id) as disadvantage_count"
            ],
            filters=[
                {"field": "CompetitorComparison.city", "operator": "=", "value": "深圳站"},
                {"field": "CompetitorComparison.price_advantage_flag", "operator": "=", "value": 2}
            ],
            limit=1
        )

        assert result["success"] is True
        assert len(result["data"]) == 1
        assert result["data"][0]["disadvantage_count"] > 0

    def test_yjp_platform_expensive_products(self):
        """Scenario: 易久批平台上，我们比它贵的商品有哪些？"""
        result = query_data(
            config_yaml=CONFIG_YAML,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.sku_name",
                "CompetitorComparison.city",
                "CompetitorComparison.product_type_first_level",
                "CompetitorComparison.ppy_price",
                "CompetitorComparison.mall_price"
            ],
            filters=[
                {"field": "CompetitorComparison.platform_id", "operator": "=", "value": "yjp"},
                {"field": "CompetitorComparison.price_advantage_flag", "operator": "=", "value": 2}
            ],
            limit=10
        )

        assert result["success"] is True
        assert len(result["data"]) > 0

        # All should be yjp platform and have sku_name
        for row in result["data"]:
            assert row["sku_name"]
            assert row["city"]
            assert row["product_type_first_level"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
