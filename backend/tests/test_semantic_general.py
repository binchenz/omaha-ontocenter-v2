from app.services.semantic_formatter import SemanticTypeFormatter


def test_format_phone():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value("13800138000", "phone")
    assert result == "138-0013-8000"


def test_format_address():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value("上海市浦东新区张江高科", "address")
    assert result == "上海市浦东新区张江高科"


def test_format_order_status():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value("pending", "order_status")
    assert result == "pending"


def test_format_quantity():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value(1500, "quantity")
    assert result == "1,500"


def test_format_weight_kg():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value(75.5, "weight_kg")
    assert result == "75.5 kg"


def test_format_email():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value("test@example.com", "email")
    assert result == "test@example.com"


def test_existing_currency_still_works():
    formatter = SemanticTypeFormatter()
    result = formatter.format_value(10000.5, "currency_cny")
    assert "1.00万" in str(result) or "10000.5" in str(result)
