"""
Test cases for CompetitorComparison object via Chat Agent.

Tests the new CompetitorComparison object to verify:
1. Basic queries work without JOIN
2. Filters are auto-applied (platform_id IS NOT NULL)
3. Minimal identification set (sku_name, city, product_type_first_level) is accessible
4. Computed properties work correctly
5. Relationships to City, Category, Platform work
"""
import pytest
from app.services.omaha import omaha_service


class TestCompetitorComparisonBasic:
    """Test basic CompetitorComparison queries."""

    def test_list_objects_includes_competitor_comparison(self):
        """Verify CompetitorComparison is in object list."""
        objects = omaha_service.list_objects(project_id=1)
        object_names = [obj["name"] for obj in objects]
        assert "CompetitorComparison" in object_names

    def test_get_competitor_comparison_schema(self):
        """Verify CompetitorComparison schema includes minimal identification set."""
        schema = omaha_service.get_schema(project_id=1, object_type="CompetitorComparison")

        # Check object exists
        assert schema["name"] == "CompetitorComparison"
        assert "竞品价格对比专用对象" in schema["description"]

        # Check minimal identification set
        property_names = [p["name"] for p in schema["properties"]]
        assert "sku_name" in property_names
        assert "city" in property_names
        assert "product_type_first_level" in property_names

        # Check detailed info NOT included
        assert "product_name" not in property_names
        assert "specification" not in property_names
        assert "brand_name" not in property_names

    def test_query_competitor_comparison_basic(self):
        """Test basic query returns data with sku_name."""
        result = omaha_service.query_data(
            project_id=1,
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

        # Check result structure
        assert "data" in result
        assert len(result["data"]) > 0

        # Check first row has required fields
        first_row = result["data"][0]
        assert "sku_name" in first_row
        assert "city" in first_row
        assert "platform_id" in first_row
        assert first_row["platform_id"]  # Should not be empty (auto-filtered)

    def test_auto_filter_platform_id(self):
        """Verify platform_id IS NOT NULL filter is auto-applied."""
        result = omaha_service.query_data(
            project_id=1,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.platform_id",
                "COUNT(*) as count"
            ],
            filters=[],
            limit=100
        )

        # All records should have non-empty platform_id
        for row in result["data"]:
            assert row["platform_id"] is not None
            assert row["platform_id"] != ""


class TestCompetitorComparisonComputedProperties:
    """Test computed properties in CompetitorComparison."""

    def test_effective_prices(self):
        """Test effective_ppy_price and effective_mall_price."""
        result = omaha_service.query_data(
            project_id=1,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.sku_name",
                "CompetitorComparison.ppy_price",
                "CompetitorComparison.ppy_promotion_price",
                "CompetitorComparison.effective_ppy_price",
                "CompetitorComparison.mall_price",
                "CompetitorComparison.mall_promotion_price",
                "CompetitorComparison.effective_mall_price"
            ],
            filters=[],
            limit=10
        )

        assert len(result["data"]) > 0
        first_row = result["data"][0]

        # effective_ppy_price should be promotion_price if exists, else ppy_price
        if first_row.get("ppy_promotion_price"):
            assert first_row["effective_ppy_price"] == first_row["ppy_promotion_price"]
        else:
            assert first_row["effective_ppy_price"] == first_row["ppy_price"]

    def test_actual_price_gap(self):
        """Test actual_price_gap computed property."""
        result = omaha_service.query_data(
            project_id=1,
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

        assert len(result["data"]) > 0
        for row in result["data"]:
            # actual_price_gap = ppy_price - mall_price
            expected_gap = float(row["ppy_price"]) - float(row["mall_price"])
            assert abs(float(row["actual_price_gap"]) - expected_gap) < 0.01

    def test_is_price_advantage(self):
        """Test is_price_advantage boolean computed property."""
        result = omaha_service.query_data(
            project_id=1,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.sku_name",
                "CompetitorComparison.price_advantage_flag",
                "CompetitorComparison.is_price_advantage"
            ],
            filters=[],
            limit=20
        )

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
        result = omaha_service.query_data(
            project_id=1,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.city",
                "COUNT(*) as total_records"
            ],
            filters=[],
            limit=20
        )

        assert len(result["data"]) > 0
        # Should have multiple cities
        cities = [row["city"] for row in result["data"]]
        assert len(set(cities)) > 1

    def test_advantage_rate_by_platform(self):
        """Test calculating price advantage rate by platform."""
        result = omaha_service.query_data(
            project_id=1,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.platform_id",
                "COUNT(*) as total",
                "SUM(CompetitorComparison.is_price_advantage) as advantage_count"
            ],
            filters=[],
            limit=20
        )

        assert len(result["data"]) > 0
        for row in result["data"]:
            assert row["total"] > 0
            assert row["advantage_count"] >= 0
            assert row["advantage_count"] <= row["total"]

    def test_expensive_products_by_category(self):
        """Test finding expensive products (flag=2) by category."""
        result = omaha_service.query_data(
            project_id=1,
            object_type="CompetitorComparison",
            selected_columns=[
                "CompetitorComparison.product_type_first_level",
                "COUNT(DISTINCT CompetitorComparison.sku_id) as expensive_sku_count"
            ],
            filters=[
                {"field": "CompetitorComparison.price_advantage_flag", "operator": "=", "value": 2}
            ],
            limit=20
        )

        assert len(result["data"]) > 0
        # Should have multiple categories
        categories = [row["product_type_first_level"] for row in result["data"]]
        assert len(set(categories)) > 1


class TestCompetitorComparisonChatScenarios:
    """Test real-world chat scenarios using CompetitorComparison."""

    def test_which_products_more_expensive(self):
        """Scenario: 哪些商品比竞品贵？"""
        result = omaha_service.query_data(
            project_id=1,
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

        assert len(result["data"]) > 0
        # All should have sku_name (no need to JOIN)
        for row in result["data"]:
            assert row["sku_name"]
            assert float(row["ppy_price"]) > float(row["mall_price"])

    def test_shenzhen_price_disadvantage(self):
        """Scenario: 深圳站有多少商品价格劣势？"""
        result = omaha_service.query_data(
            project_id=1,
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

        assert len(result["data"]) == 1
        assert result["data"][0]["disadvantage_count"] > 0

    def test_yjp_platform_expensive_products(self):
        """Scenario: 易久批平台上，我们比它贵的商品有哪些？"""
        result = omaha_service.query_data(
            project_id=1,
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

        assert len(result["data"]) > 0
        # All should be yjp platform and have sku_name
        for row in result["data"]:
            assert row["sku_name"]
            assert row["city"]
            assert row["product_type_first_level"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
