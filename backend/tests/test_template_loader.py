from app.services.ontology.template_loader import TemplateLoader


def test_list_industries_includes_retail():
    industries = TemplateLoader.list_industries()
    values = [i["value"] for i in industries]
    assert "retail" in values
    retail = next(i for i in industries if i["value"] == "retail")
    assert retail["display_name"] == "零售/电商"
    assert retail["domain"] == "retail"


def test_load_retail_template():
    template = TemplateLoader.load("retail")
    assert template is not None
    assert template["industry"] == "retail"
    object_names = [obj["name"] for obj in template["objects"]]
    assert "订单" in object_names
    assert "客户" in object_names
    assert len(template["relationships"]) >= 1


def test_load_unknown_industry_returns_none():
    assert TemplateLoader.load("nonexistent") is None
