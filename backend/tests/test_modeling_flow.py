"""End-to-end test of the conversational modeling flow."""
import pytest
import pandas as pd
from unittest.mock import MagicMock
from app.services.agent.toolkit import AgentToolkit
from app.services.data.uploaded_table_store import UploadedTableStore
from app.services.ontology.draft_store import OntologyDraftStore
from app.schemas.auto_model import InferredObject, InferredProperty


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Ensure templates dir is reachable from tmp_path
    templates = tmp_path / "configs" / "templates"
    templates.mkdir(parents=True, exist_ok=True)
    (templates / "retail.yaml").write_text(
        "industry: retail\n"
        "display_name: 零售/电商\n"
        "domain: retail\n"
        "objects:\n"
        "  - name: 订单\n"
        "    description: 客户的采购订单\n"
        "    properties:\n"
        "      - name: 客户\n"
        "        data_type: string\n"
        "        semantic_type: customer_id\n"
        "      - name: 金额\n"
        "        data_type: number\n"
        "        semantic_type: currency_cny\n"
        "relationships: []\n",
        encoding="utf-8",
    )
    yield


def test_full_modeling_flow(monkeypatch):
    # TemplateLoader uses an absolute path resolved at import time. Override it
    # to point at the tmp_path templates dir so this test is hermetic.
    from app.services.ontology import template_loader
    monkeypatch.setattr(
        template_loader, "_TEMPLATE_DIR", template_loader.Path("configs/templates")
    )

    # Setup: project + uploaded data
    fake_project = MagicMock(tenant_id=42, owner_id=42, setup_stage="cleaning")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = fake_project

    df = pd.DataFrame({"客户": ["a", "b"], "金额": [100, 200]})
    UploadedTableStore.save(1, 2, "orders", df)

    # Stub LLM
    monkeypatch.setattr(
        "app.services.ontology.inferrer.OntologyInferrer.__init__",
        lambda self: None,
    )
    monkeypatch.setattr(
        "app.services.ontology.inferrer.OntologyInferrer.infer_table",
        lambda self, table, datasource_id, template_hint=None: InferredObject(
            name="订单",
            source_entity="orders",
            datasource_id="upload",
            datasource_type="csv",
            properties=[
                InferredProperty(name="客户", data_type="string", semantic_type=None),
                InferredProperty(name="金额", data_type="number", semantic_type=None),
            ],
        ),
    )
    monkeypatch.setattr(
        "app.services.ontology.inferrer.OntologyInferrer.infer_relationships_by_naming",
        lambda self, objs: [],
    )

    # Stub OntologyImporter
    imported = {}

    class FakeImporter:
        def __init__(self, _db):
            pass

        def import_dict(self, tenant_id, config):
            imported["tenant_id"] = tenant_id
            imported["object_count"] = len(config["ontology"]["objects"])
            return {"objects_created": len(config["ontology"]["objects"]), "objects_updated": 0, "relationships_created": 0}

    monkeypatch.setattr("app.services.agent.toolkit.OntologyImporter", FakeImporter)

    toolkit = AgentToolkit(omaha_service=MagicMock(), project_id=1, session_id=2, db=db)

    # 1. Load template
    r = toolkit.execute_tool("load_template", {"industry": "retail"})
    assert r["success"] is True
    assert r["data"]["display_name"] == "零售/电商"

    # 2. Scan tables
    r = toolkit.execute_tool("scan_tables", {})
    assert r["success"] is True
    assert r["data"]["tables"][0]["name"] == "orders"

    # 3. Infer ontology with retail hint
    r = toolkit.execute_tool("infer_ontology", {"industry": "retail"})
    assert r["success"] is True
    assert r["data"]["objects_count"] == 1
    # Template back-fill should give 客户/金额 their semantic types
    obj = r["data"]["objects"][0]
    props = {p["name"]: p.get("semantic_type") for p in obj["properties"]}
    assert props["客户"] == "customer_id"
    assert props["金额"] == "currency_cny"

    # Draft persisted
    draft = OntologyDraftStore.load(1, 2)
    assert draft is not None
    assert len(draft["objects"]) == 1

    # 4. Confirm
    r = toolkit.execute_tool("confirm_ontology", {})
    assert r["success"] is True
    assert imported["object_count"] == 1
    assert fake_project.setup_stage == "ready"
    assert OntologyDraftStore.load(1, 2) is None

    # 5. Edit ontology (rename property)
    fake_obj = MagicMock(id=10, name="订单")

    class FakeStore:
        def __init__(self, _db):
            pass

        def get_object(self, tenant_id, name):
            return fake_obj

        def rename_property(self, object_id, old_name, new_name):
            return True

    monkeypatch.setattr("app.services.agent.toolkit.OntologyStore", FakeStore)
    r = toolkit.execute_tool("edit_ontology", {
        "action": "rename_property",
        "object_name": "订单",
        "property_name": "金额",
        "new_value": "总金额",
    })
    assert r["success"] is True
