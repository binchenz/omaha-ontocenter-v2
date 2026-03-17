"""
Unit tests for semantic type validation and formatting.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.semantic_validator import semantic_type_validator


def test_currency_validation():
    """Test currency semantic type validation."""
    prop_def = {
        "semantic_type": "currency",
        "currency": "CNY"
    }

    # Valid currency values
    result = semantic_type_validator.validate_property(100.50, prop_def)
    assert result["valid"] == True
    assert result["value"] == 100.50
    assert result["formatted"] == "¥100.50"

    result = semantic_type_validator.validate_property(0, prop_def)
    assert result["valid"] == True
    assert result["formatted"] == "¥0.00"

    result = semantic_type_validator.validate_property(None, prop_def)
    assert result["valid"] == True
    assert result["value"] is None

    # Invalid currency value
    result = semantic_type_validator.validate_property("invalid", prop_def)
    assert result["valid"] == False
    assert "error" in result

    print("✅ test_currency_validation passed")


def test_percentage_validation():
    """Test percentage semantic type validation."""
    prop_def = {
        "semantic_type": "percentage"
    }

    # Valid percentage values (0-1 range)
    result = semantic_type_validator.validate_property(0.25, prop_def)
    assert result["valid"] == True
    assert result["value"] == 0.25
    assert result["formatted"] == "25.00%"

    result = semantic_type_validator.validate_property(0, prop_def)
    assert result["valid"] == True
    assert result["formatted"] == "0.00%"

    result = semantic_type_validator.validate_property(1, prop_def)
    assert result["valid"] == True
    assert result["formatted"] == "100.00%"

    # Out of range (warning but still valid)
    result = semantic_type_validator.validate_property(1.5, prop_def)
    assert result["valid"] == True
    assert result["formatted"] == "150.00%"
    assert "warning" in result

    result = semantic_type_validator.validate_property(-0.1, prop_def)
    assert result["valid"] == True
    assert "warning" in result

    # Invalid percentage value
    result = semantic_type_validator.validate_property("invalid", prop_def)
    assert result["valid"] == False
    assert "error" in result

    print("✅ test_percentage_validation passed")


def test_enum_validation():
    """Test enum semantic type validation."""
    prop_def = {
        "semantic_type": "enum",
        "enum_values": [
            {"value": "yjp", "label": "易久批"},
            {"value": "xsj", "label": "鲜世纪"},
            {"value": "jd_ws", "label": "京东万商"}
        ]
    }

    # Valid enum values
    result = semantic_type_validator.validate_property("yjp", prop_def)
    assert result["valid"] == True
    assert result["value"] == "yjp"
    assert result["formatted"] == "yjp (易久批)"

    result = semantic_type_validator.validate_property("xsj", prop_def)
    assert result["valid"] == True
    assert result["formatted"] == "xsj (鲜世纪)"

    # Invalid enum value
    result = semantic_type_validator.validate_property("invalid_platform", prop_def)
    assert result["valid"] == False
    assert "error" in result
    assert "Allowed" in result["error"]

    # Null value
    result = semantic_type_validator.validate_property(None, prop_def)
    assert result["valid"] == True
    assert result["value"] is None

    print("✅ test_enum_validation passed")


def test_date_validation():
    """Test date semantic type validation."""
    prop_def = {
        "semantic_type": "date"
    }

    # Valid date string
    result = semantic_type_validator.validate_property("2026-03-16", prop_def)
    assert result["valid"] == True
    assert result["value"] == "2026-03-16"
    assert result["formatted"] == "2026-03-16"

    # Different date formats
    result = semantic_type_validator.validate_property("2026/03/16", prop_def)
    assert result["valid"] == True
    assert result["formatted"] == "2026-03-16"

    # Invalid date
    result = semantic_type_validator.validate_property("invalid-date", prop_def)
    assert result["valid"] == False
    assert "error" in result

    # Null value
    result = semantic_type_validator.validate_property(None, prop_def)
    assert result["valid"] == True
    assert result["value"] is None

    print("✅ test_date_validation passed")


def test_id_validation():
    """Test ID semantic type validation."""
    prop_def = {
        "semantic_type": "id"
    }

    # Valid ID values
    result = semantic_type_validator.validate_property(12345, prop_def)
    assert result["valid"] == True
    assert result["value"] == 12345
    assert result["formatted"] == "12345"

    result = semantic_type_validator.validate_property("SKU-12345", prop_def)
    assert result["valid"] == True
    assert result["value"] == "SKU-12345"

    # Invalid ID type
    result = semantic_type_validator.validate_property(12.34, prop_def)
    assert result["valid"] == False
    assert "error" in result

    # Null value
    result = semantic_type_validator.validate_property(None, prop_def)
    assert result["valid"] == True
    assert result["value"] is None

    print("✅ test_id_validation passed")


def test_format_query_results():
    """Test formatting complete query results."""
    results = [
        {
            "sku_id": 12345,
            "sku_name": "可口可乐",
            "ppy_price": 3.50,
            "gross_margin": 0.25,
            "platform_id": "yjp",
            "p_date": "2026-03-16"
        },
        {
            "sku_id": 67890,
            "sku_name": "雪碧",
            "ppy_price": 3.00,
            "gross_margin": 0.30,
            "platform_id": "xsj",
            "p_date": "2026-03-16"
        }
    ]

    schema = {
        "sku_id": {"semantic_type": "id"},
        "sku_name": {"type": "string"},
        "ppy_price": {"semantic_type": "currency", "currency": "CNY"},
        "gross_margin": {"semantic_type": "percentage"},
        "platform_id": {
            "semantic_type": "enum",
            "enum_values": [
                {"value": "yjp", "label": "易久批"},
                {"value": "xsj", "label": "鲜世纪"}
            ]
        },
        "p_date": {"semantic_type": "date"}
    }

    formatted = semantic_type_validator.format_query_results(results, schema)

    # Check formatted results
    assert len(formatted["formatted_results"]) == 2
    assert formatted["formatted_results"][0]["ppy_price"]["formatted"] == "¥3.50"
    assert formatted["formatted_results"][0]["gross_margin"]["formatted"] == "25.00%"
    assert formatted["formatted_results"][0]["platform_id"]["formatted"] == "yjp (易久批)"
    assert formatted["formatted_results"][1]["platform_id"]["formatted"] == "xsj (鲜世纪)"

    # Check no validation errors
    assert len(formatted["validation_errors"]) == 0

    print("✅ test_format_query_results passed")


def test_format_query_results_with_errors():
    """Test formatting query results with validation errors."""
    results = [
        {
            "sku_id": 12345,
            "ppy_price": "invalid_price",  # Invalid currency
            "platform_id": "unknown_platform"  # Invalid enum
        }
    ]

    schema = {
        "sku_id": {"semantic_type": "id"},
        "ppy_price": {"semantic_type": "currency", "currency": "CNY"},
        "platform_id": {
            "semantic_type": "enum",
            "enum_values": [
                {"value": "yjp", "label": "易久批"},
                {"value": "xsj", "label": "鲜世纪"}
            ]
        }
    }

    formatted = semantic_type_validator.format_query_results(results, schema)

    # Check validation errors
    assert len(formatted["validation_errors"]) == 2
    assert any(e["column"] == "ppy_price" for e in formatted["validation_errors"])
    assert any(e["column"] == "platform_id" for e in formatted["validation_errors"])

    print("✅ test_format_query_results_with_errors passed")


if __name__ == "__main__":
    print("Running semantic type validation tests...\n")
    test_currency_validation()
    test_percentage_validation()
    test_enum_validation()
    test_date_validation()
    test_id_validation()
    test_format_query_results()
    test_format_query_results_with_errors()
    print("\n" + "="*80)
    print("✅ All tests passed!")
