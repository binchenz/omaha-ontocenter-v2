from tests.conftest import LEGACY_FINANCIAL_CONFIG
"""
Test cases for Industry object via Tushare datasource.

Tests the Industry object to verify:
1. Industry data retrieval works correctly
2. Industry field is present in results
3. Multiple industries can be queried
"""
import pytest
import os


class TestIndustryBasic:
    """Test basic Industry queries."""

    def test_query_industry_list(self):
        """Test querying industry data from Tushare."""
        import sys
        sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')
        from app.services.legacy.financial.omaha import OmahaService

        config_path = str(LEGACY_FINANCIAL_CONFIG)
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Industry",
            selected_columns=["industry"],
            filters=[],
            limit=50
        )

        # Check result structure
        assert result["success"] is True
        assert "data" in result
        assert len(result["data"]) > 0

        # Check industry names are present
        industries = [row["industry"] for row in result["data"]]
        assert len(industries) > 0
        # Industry field should be populated
        assert all(ind for ind in industries), "All industries should have non-empty values"
        print(f"✓ Found {len(result['data'])} records with industries")

    def test_industry_has_required_fields(self):
        """Test that Industry object returns required fields."""
        from app.services.legacy.financial.omaha import OmahaService

        config_path = str(LEGACY_FINANCIAL_CONFIG)
        with open(config_path, 'r', encoding='utf-8') as f:
            config_yaml = f.read()

        os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

        service = OmahaService()
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="Industry",
            selected_columns=["industry"],
            filters=[],
            limit=10
        )

        # Check result
        assert result["success"] is True
        assert len(result["data"]) > 0

        # Check that industry field exists in results
        for row in result["data"]:
            assert "industry" in row
            assert row["industry"] is not None
        print(f"✓ Industry field present in all {len(result['data'])} records")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
