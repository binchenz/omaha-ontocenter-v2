"""
Semantic type validation and formatting for query results.

Validates and formats query results based on semantic_type definitions:
- currency: validates numeric values, formats with currency symbol
- percentage: validates 0-1 range, formats as percentage
- enum: validates against allowed values
- date: validates date format
- id: validates integer/string ID format
"""
from typing import Any, Dict, List, Optional
from decimal import Decimal
from datetime import date, datetime


class SemanticTypeValidator:
    """Validates and formats values based on semantic types."""

    def validate_property(
        self,
        value: Any,
        prop_def: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a property value against its semantic type definition.

        Args:
            value: The value to validate
            prop_def: Property definition with semantic_type, type, etc.

        Returns:
            Dict with:
            - valid: bool
            - value: original or formatted value
            - error: error message if invalid
            - formatted: human-readable formatted value
        """
        semantic_type = prop_def.get("semantic_type")

        if semantic_type == "currency":
            return self._validate_currency(value, prop_def)
        elif semantic_type == "percentage":
            return self._validate_percentage(value, prop_def)
        elif semantic_type == "enum":
            return self._validate_enum(value, prop_def)
        elif semantic_type == "date":
            return self._validate_date(value, prop_def)
        elif semantic_type == "id":
            return self._validate_id(value, prop_def)
        else:
            # No semantic type or unknown type - pass through
            return {
                "valid": True,
                "value": value,
                "formatted": str(value) if value is not None else None
            }

    def _validate_currency(
        self,
        value: Any,
        prop_def: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate currency value."""
        if value is None:
            return {"valid": True, "value": None, "formatted": None}

        try:
            decimal_value = Decimal(str(value))

            currency = prop_def.get("currency", "CNY")
            currency_symbols = {
                "CNY": "¥",
                "USD": "$",
                "EUR": "€",
                "GBP": "£"
            }
            symbol = currency_symbols.get(currency, currency)

            # Format with 2 decimal places
            formatted = f"{symbol}{decimal_value:.2f}"

            return {
                "valid": True,
                "value": float(decimal_value),
                "formatted": formatted
            }
        except (ValueError, TypeError, Exception) as e:
            return {
                "valid": False,
                "value": value,
                "error": f"Invalid currency value: {value}",
                "formatted": str(value)
            }

    def _validate_percentage(
        self,
        value: Any,
        prop_def: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate percentage value (expected range: 0-1)."""
        if value is None:
            return {"valid": True, "value": None, "formatted": None}

        try:
            float_value = float(value)

            # Warn if outside typical 0-1 range (but don't fail)
            warning = None
            if float_value < 0 or float_value > 1:
                warning = f"Percentage value {float_value} outside typical 0-1 range"

            # Format as percentage
            formatted = f"{float_value * 100:.2f}%"

            result = {
                "valid": True,
                "value": float_value,
                "formatted": formatted
            }
            if warning:
                result["warning"] = warning

            return result
        except (ValueError, TypeError) as e:
            return {
                "valid": False,
                "value": value,
                "error": f"Invalid percentage value: {value}",
                "formatted": str(value)
            }

    def _validate_enum(
        self,
        value: Any,
        prop_def: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate enum value against allowed values."""
        if value is None:
            return {"valid": True, "value": None, "formatted": None}

        enum_values = prop_def.get("enum_values", [])
        if not enum_values:
            # No enum values defined - pass through
            return {
                "valid": True,
                "value": value,
                "formatted": str(value)
            }

        # Check if value is in allowed values
        allowed_values = [e.get("value") for e in enum_values]
        if value not in allowed_values:
            return {
                "valid": False,
                "value": value,
                "error": f"Invalid enum value: {value}. Allowed: {allowed_values}",
                "formatted": str(value)
            }

        # Find label for this value
        label = next(
            (e.get("label") for e in enum_values if e.get("value") == value),
            str(value)
        )

        return {
            "valid": True,
            "value": value,
            "formatted": f"{value} ({label})"
        }

    def _validate_date(
        self,
        value: Any,
        prop_def: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate date value."""
        if value is None:
            return {"valid": True, "value": None, "formatted": None}

        try:
            # Handle different date formats
            if isinstance(value, (date, datetime)):
                date_value = value if isinstance(value, date) else value.date()
                formatted = date_value.strftime("%Y-%m-%d")
                return {
                    "valid": True,
                    "value": formatted,
                    "formatted": formatted
                }
            elif isinstance(value, str):
                # Try to parse string date
                try:
                    date_value = datetime.strptime(value, "%Y-%m-%d").date()
                    formatted = date_value.strftime("%Y-%m-%d")
                    return {
                        "valid": True,
                        "value": formatted,
                        "formatted": formatted
                    }
                except ValueError:
                    # Try other common formats
                    for fmt in ["%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]:
                        try:
                            date_value = datetime.strptime(value, fmt).date()
                            formatted = date_value.strftime("%Y-%m-%d")
                            return {
                                "valid": True,
                                "value": formatted,
                                "formatted": formatted
                            }
                        except ValueError:
                            continue
                    raise ValueError(f"Cannot parse date: {value}")
            else:
                raise ValueError(f"Unsupported date type: {type(value)}")
        except (ValueError, TypeError) as e:
            return {
                "valid": False,
                "value": value,
                "error": f"Invalid date value: {value}",
                "formatted": str(value)
            }

    def _validate_id(
        self,
        value: Any,
        prop_def: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate ID value."""
        if value is None:
            return {"valid": True, "value": None, "formatted": None}

        # IDs can be integers or strings
        if isinstance(value, (int, str)):
            return {
                "valid": True,
                "value": value,
                "formatted": str(value)
            }
        else:
            return {
                "valid": False,
                "value": value,
                "error": f"Invalid ID type: {type(value)}",
                "formatted": str(value)
            }

    def format_query_results(
        self,
        results: List[Dict[str, Any]],
        schema: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Format query results with semantic type validation.

        Args:
            results: List of result rows (dicts)
            schema: Dict mapping column names to property definitions

        Returns:
            Dict with:
            - formatted_results: List of formatted rows
            - validation_errors: List of validation errors
            - warnings: List of warnings
        """
        formatted_results = []
        validation_errors = []
        warnings = []

        for row_idx, row in enumerate(results):
            formatted_row = {}
            for col_name, value in row.items():
                prop_def = schema.get(col_name, {})
                validation = self.validate_property(value, prop_def)

                formatted_row[col_name] = {
                    "value": validation["value"],
                    "formatted": validation.get("formatted")
                }

                if not validation.get("valid", True):
                    validation_errors.append({
                        "row": row_idx,
                        "column": col_name,
                        "error": validation.get("error")
                    })

                if "warning" in validation:
                    warnings.append({
                        "row": row_idx,
                        "column": col_name,
                        "warning": validation["warning"]
                    })

            formatted_results.append(formatted_row)

        return {
            "formatted_results": formatted_results,
            "validation_errors": validation_errors,
            "warnings": warnings
        }


# Global instance
semantic_type_validator = SemanticTypeValidator()
