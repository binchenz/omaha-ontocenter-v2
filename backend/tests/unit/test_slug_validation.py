import pytest
from app.services.ontology.slug import _validate_sql_identifier


class TestValidateSqlIdentifier:
    def test_valid_simple_name(self):
        assert _validate_sql_identifier("ontology_objects") == "ontology_objects"

    def test_valid_with_numbers(self):
        assert _validate_sql_identifier("table2") == "table2"

    def test_rejects_sql_injection(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_sql_identifier("users; DROP TABLE users--")

    def test_rejects_spaces(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_sql_identifier("my table")

    def test_rejects_semicolons(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_sql_identifier("table;")

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_sql_identifier("")

    def test_rejects_leading_number(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_sql_identifier("1table")
