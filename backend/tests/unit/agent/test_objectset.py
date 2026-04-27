"""Tests for ObjectSet core and compiler."""

import pytest
from app.services.agent.objectset import ObjectSet, Filter, Sort
from app.services.agent.objectset.compiler import compile_query_args


class TestObjectSet:
    """Test ObjectSet immutability and methods."""

    def test_where_returns_new_objectset(self):
        """where() should return new ObjectSet, original unchanged."""
        original = ObjectSet(object_type="Stock")
        filtered = original.where(symbol="AAPL")

        # Original unchanged
        assert len(original.filters) == 0
        # New instance created
        assert filtered is not original
        # New instance has filter
        assert len(filtered.filters) == 1
        assert filtered.filters[0].field == "symbol"
        assert filtered.filters[0].operator == "eq"
        assert filtered.filters[0].value == "AAPL"

    def test_where_multiple_conditions(self):
        """where() with multiple conditions should add all filters."""
        obj_set = ObjectSet(object_type="Stock").where(symbol="AAPL", price=150)
        assert len(obj_set.filters) == 2
        fields = {f.field for f in obj_set.filters}
        assert fields == {"symbol", "price"}

    def test_where_chaining(self):
        """where() calls should chain and accumulate filters."""
        obj_set = (
            ObjectSet(object_type="Stock")
            .where(symbol="AAPL")
            .where(price=150)
        )
        assert len(obj_set.filters) == 2

    def test_select_replaces_selected(self):
        """select() should replace selected columns."""
        obj_set = ObjectSet(object_type="Stock").select("symbol", "price")
        assert obj_set.selected == ("symbol", "price")

    def test_select_replaces_previous(self):
        """select() should replace previous selection."""
        obj_set = (
            ObjectSet(object_type="Stock")
            .select("symbol", "price")
            .select("symbol", "volume")
        )
        assert obj_set.selected == ("symbol", "volume")

    def test_order_by_appends_sort(self):
        """order_by() should append sort specification."""
        obj_set = ObjectSet(object_type="Stock").order_by("price", desc=True)
        assert len(obj_set.sorts) == 1
        assert obj_set.sorts[0].field == "price"
        assert obj_set.sorts[0].desc is True

    def test_order_by_chaining(self):
        """order_by() calls should chain and accumulate sorts."""
        obj_set = (
            ObjectSet(object_type="Stock")
            .order_by("price", desc=True)
            .order_by("symbol")
        )
        assert len(obj_set.sorts) == 2

    def test_limit_to_sets_limit(self):
        """limit_to() should set result limit."""
        obj_set = ObjectSet(object_type="Stock").limit_to(10)
        assert obj_set.limit == 10

    def test_limit_to_replaces_previous(self):
        """limit_to() should replace previous limit."""
        obj_set = (
            ObjectSet(object_type="Stock")
            .limit_to(10)
            .limit_to(20)
        )
        assert obj_set.limit == 20

    def test_immutability_frozen(self):
        """ObjectSet should be frozen (immutable)."""
        obj_set = ObjectSet(object_type="Stock")
        with pytest.raises(AttributeError):
            obj_set.object_type = "Bond"

    def test_filter_immutability(self):
        """Filter should be frozen (immutable)."""
        f = Filter(field="symbol", operator="eq", value="AAPL")
        with pytest.raises(AttributeError):
            f.field = "price"

    def test_sort_immutability(self):
        """Sort should be frozen (immutable)."""
        s = Sort(field="price", desc=True)
        with pytest.raises(AttributeError):
            s.desc = False


class TestCompileQueryArgs:
    """Test compile_query_args compiler."""

    def test_compile_basic_objectset(self):
        """compile_query_args should handle basic ObjectSet."""
        obj_set = ObjectSet(object_type="Stock")
        compiled = compile_query_args(obj_set)

        assert compiled["object_type"] == "Stock"
        assert compiled["selected_columns"] is None
        assert compiled["filters"] == []
        assert compiled["limit"] is None

    def test_compile_with_eq_filter(self):
        """compile_query_args should map eq operator to =."""
        obj_set = ObjectSet(object_type="Stock").where(symbol="AAPL")
        compiled = compile_query_args(obj_set)

        assert len(compiled["filters"]) == 1
        assert compiled["filters"][0]["field"] == "symbol"
        assert compiled["filters"][0]["operator"] == "="
        assert compiled["filters"][0]["value"] == "AAPL"

    def test_compile_with_range_filters(self):
        """compile_query_args should map range operators correctly."""
        obj_set = (
            ObjectSet(object_type="Stock")
            .where(price=150)  # eq
        )
        # Add range filters manually to test operator mapping
        from app.services.agent.objectset import Filter
        obj_set = ObjectSet(
            object_type="Stock",
            filters=(
                Filter(field="price", operator="gte", value=100),
                Filter(field="price", operator="lte", value=200),
            )
        )
        compiled = compile_query_args(obj_set)

        assert len(compiled["filters"]) == 2
        assert compiled["filters"][0]["operator"] == ">="
        assert compiled["filters"][1]["operator"] == "<="

    def test_compile_with_selected_columns(self):
        """compile_query_args should include selected_columns."""
        obj_set = ObjectSet(object_type="Stock").select("symbol", "price", "volume")
        compiled = compile_query_args(obj_set)

        assert compiled["selected_columns"] == ["symbol", "price", "volume"]

    def test_compile_with_limit(self):
        """compile_query_args should include limit."""
        obj_set = ObjectSet(object_type="Stock").limit_to(50)
        compiled = compile_query_args(obj_set)

        assert compiled["limit"] == 50

    def test_compile_complex_query(self):
        """compile_query_args should handle complex query with all components."""
        obj_set = (
            ObjectSet(object_type="Stock")
            .where(symbol="AAPL")
            .select("symbol", "price", "volume")
            .order_by("price", desc=True)
            .limit_to(10)
        )
        compiled = compile_query_args(obj_set)

        assert compiled["object_type"] == "Stock"
        assert compiled["selected_columns"] == ["symbol", "price", "volume"]
        assert len(compiled["filters"]) == 1
        assert compiled["filters"][0]["operator"] == "="
        assert compiled["limit"] == 10

    def test_compile_operator_mapping(self):
        """compile_query_args should map all operators correctly."""
        operators = ["eq", "ne", "gt", "gte", "lt", "lte", "contains", "in"]
        expected = ["=", "!=", ">", ">=", "<", "<=", "LIKE", "IN"]

        for op, expected_op in zip(operators, expected):
            obj_set = ObjectSet(
                object_type="Stock",
                filters=(Filter(field="test", operator=op, value="value"),)
            )
            compiled = compile_query_args(obj_set)
            assert compiled["filters"][0]["operator"] == expected_op

    def test_compile_empty_selected_returns_none(self):
        """compile_query_args should return None for empty selected."""
        obj_set = ObjectSet(object_type="Stock", selected=())
        compiled = compile_query_args(obj_set)
        assert compiled["selected_columns"] is None

    def test_compile_multiple_filters(self):
        """compile_query_args should handle multiple filters."""
        obj_set = (
            ObjectSet(object_type="Stock")
            .where(symbol="AAPL")
            .where(price=150)
        )
        compiled = compile_query_args(obj_set)

        assert len(compiled["filters"]) == 2
        assert compiled["filters"][0]["field"] == "symbol"
        assert compiled["filters"][1]["field"] == "price"


class TestObjectSetIntegration:
    """Integration tests for ObjectSet with compiler."""

    def test_full_query_building_flow(self):
        """Test complete query building flow."""
        obj_set = (
            ObjectSet(object_type="Stock")
            .where(symbol="AAPL", market="US")
            .select("symbol", "price", "volume")
            .order_by("price", desc=True)
            .limit_to(100)
        )

        compiled = compile_query_args(obj_set)

        assert compiled["object_type"] == "Stock"
        assert len(compiled["filters"]) == 2
        assert compiled["selected_columns"] == ["symbol", "price", "volume"]
        assert compiled["limit"] == 100

    def test_chaining_preserves_immutability(self):
        """Test that chaining preserves immutability of intermediate objects."""
        obj_set1 = ObjectSet(object_type="Stock")
        obj_set2 = obj_set1.where(symbol="AAPL")
        obj_set3 = obj_set2.select("symbol", "price")

        # Each should be independent
        assert len(obj_set1.filters) == 0
        assert len(obj_set1.selected) == 0

        assert len(obj_set2.filters) == 1
        assert len(obj_set2.selected) == 0

        assert len(obj_set3.filters) == 1
        assert len(obj_set3.selected) == 2
