import pytest
import pandas as pd
from unittest.mock import MagicMock
from app.services.agent_tools import AgentToolkit
from app.services.uploaded_table_store import UploadedTableStore


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


@pytest.fixture
def toolkit():
    return AgentToolkit(omaha_service=MagicMock(), project_id=1, session_id=2)


def test_load_template_known_industry(toolkit, monkeypatch):
    from app.services import template_loader
    monkeypatch.setattr(
        template_loader.TemplateLoader, "load",
        staticmethod(lambda industry: {"industry": industry, "display_name": "test", "objects": [{"name": "订单", "properties": []}], "relationships": []})
    )
    result = toolkit.execute_tool("load_template", {"industry": "retail"})
    assert result["success"] is True


def test_load_template_unknown_industry(toolkit, monkeypatch):
    from app.services import template_loader
    monkeypatch.setattr(
        template_loader.TemplateLoader, "load",
        staticmethod(lambda industry: None)
    )
    result = toolkit.execute_tool("load_template", {"industry": "unknown"})
    assert result["success"] is False


def test_scan_tables_with_uploaded_data(toolkit):
    df = pd.DataFrame({"客户": ["a", "b"], "金额": [100, 200]})
    UploadedTableStore.save(1, 2, "orders", df)
    result = toolkit.execute_tool("scan_tables", {})
    assert result["success"] is True
    assert len(result["data"]["tables"]) == 1
    table = result["data"]["tables"][0]
    assert table["name"] == "orders"
    assert table["row_count"] == 2


def test_scan_tables_no_uploaded_data(toolkit):
    result = toolkit.execute_tool("scan_tables", {})
    assert result["success"] is False


def test_infer_ontology_writes_draft(toolkit, monkeypatch):
    df = pd.DataFrame({"客户": ["a"], "金额": [100]})
    UploadedTableStore.save(1, 2, "orders", df)

    from app.services import ontology_inferrer
    from app.schemas.auto_model import InferredObject, InferredProperty

    fake_obj = InferredObject(
        name="订单",
        source_entity="orders",
        datasource_id="upload",
        datasource_type="csv",
        properties=[
            InferredProperty(name="客户", data_type="string", semantic_type="id"),
            InferredProperty(name="金额", data_type="number", semantic_type="currency_cny"),
        ],
    )

    monkeypatch.setattr(
        ontology_inferrer.OntologyInferrer, "__init__",
        lambda self: None,
    )
    monkeypatch.setattr(
        ontology_inferrer.OntologyInferrer, "infer_table",
        lambda self, table, datasource_id, template_hint=None: fake_obj,
    )
    monkeypatch.setattr(
        ontology_inferrer.OntologyInferrer, "infer_relationships_by_naming",
        lambda self, objs: [],
    )

    result = toolkit.execute_tool("infer_ontology", {})
    assert result["success"] is True
    assert result["data"]["objects_count"] == 1

    from app.services.ontology_draft_store import OntologyDraftStore
    draft = OntologyDraftStore.load(1, 2)
    assert draft is not None
    assert len(draft["objects"]) == 1
    assert draft["objects"][0]["name"] == "订单"


def test_infer_ontology_overwrites_existing_draft(toolkit, monkeypatch):
    from app.services.ontology_draft_store import OntologyDraftStore
    OntologyDraftStore.save(1, 2, [{"name": "old"}], [], [])

    df = pd.DataFrame({"x": [1]})
    UploadedTableStore.save(1, 2, "t", df)

    from app.services import ontology_inferrer
    from app.schemas.auto_model import InferredObject

    monkeypatch.setattr(ontology_inferrer.OntologyInferrer, "__init__", lambda self: None)
    monkeypatch.setattr(
        ontology_inferrer.OntologyInferrer, "infer_table",
        lambda self, table, datasource_id, template_hint=None: InferredObject(
            name="新对象", source_entity="t", datasource_id="upload",
            datasource_type="csv", properties=[],
        ),
    )
    monkeypatch.setattr(
        ontology_inferrer.OntologyInferrer, "infer_relationships_by_naming",
        lambda self, objs: [],
    )

    toolkit.execute_tool("infer_ontology", {})
    draft = OntologyDraftStore.load(1, 2)
    assert draft["objects"][0]["name"] == "新对象"


def test_infer_ontology_no_uploaded_data(toolkit):
    result = toolkit.execute_tool("infer_ontology", {})
    assert result["success"] is False


def test_confirm_ontology_persists_draft_and_clears(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from app.services.ontology_draft_store import OntologyDraftStore
    OntologyDraftStore.save(
        project_id=1, session_id=2,
        objects=[{
            "name": "订单",
            "source_entity": "orders",
            "datasource_id": "upload",
            "datasource_type": "csv",
            "properties": [{"name": "金额", "data_type": "number", "semantic_type": "currency_cny"}],
        }],
        relationships=[],
        warnings=[],
    )

    fake_project = MagicMock(tenant_id=42, owner_id=42, setup_stage="modeling")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = fake_project

    imported = {}
    from app.services import agent_tools as at_mod

    class FakeImporter:
        def __init__(self, _db):
            pass
        def import_dict(self, tenant_id, config):
            imported["tenant_id"] = tenant_id
            imported["config"] = config
            return {"objects_created": 1, "objects_updated": 0, "relationships_created": 0}

    monkeypatch.setattr(at_mod, "OntologyImporter", FakeImporter)

    toolkit = AgentToolkit(omaha_service=MagicMock(), project_id=1, session_id=2, db=db)
    result = toolkit.execute_tool("confirm_ontology", {})

    assert result["success"] is True
    assert result["data"]["objects_created"] == 1
    assert imported["tenant_id"] == 42
    assert OntologyDraftStore.load(1, 2) is None
    assert fake_project.setup_stage == "ready"
    db.commit.assert_called()


def test_confirm_ontology_no_draft(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = MagicMock()
    toolkit = AgentToolkit(omaha_service=MagicMock(), project_id=99, session_id=99, db=db)
    result = toolkit.execute_tool("confirm_ontology", {})
    assert result["success"] is False
    assert "draft" in result["error"].lower() or "草稿" in result["error"]


def test_edit_ontology_blocks_non_ready_stage():
    fake_project = MagicMock(tenant_id=42, owner_id=42, setup_stage="modeling")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = fake_project
    toolkit = AgentToolkit(omaha_service=MagicMock(), project_id=1, session_id=2, db=db)
    result = toolkit.execute_tool("edit_ontology", {
        "action": "rename_object",
        "object_name": "订单",
        "new_value": "采购单",
    })
    assert result["success"] is False
    assert "ready" in result["error"].lower() or "已确认" in result["error"]


def test_edit_ontology_rename_property(monkeypatch):
    from app.services import agent_tools as at_mod

    fake_project = MagicMock(tenant_id=42, owner_id=42, setup_stage="ready")
    fake_object = MagicMock(id=10)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = fake_project

    calls = []

    class FakeStore:
        def __init__(self, _db):
            pass
        def get_object(self, tenant_id, name):
            return fake_object
        def rename_property(self, object_id, old_name, new_name):
            calls.append(("rename_property", object_id, old_name, new_name))
            return True

    monkeypatch.setattr(at_mod, "OntologyStore", FakeStore)

    toolkit = AgentToolkit(omaha_service=MagicMock(), project_id=1, session_id=2, db=db)
    result = toolkit.execute_tool("edit_ontology", {
        "action": "rename_property",
        "object_name": "订单",
        "property_name": "金额",
        "new_value": "总金额",
    })
    assert result["success"] is True
    assert ("rename_property", 10, "金额", "总金额") in calls


def test_edit_ontology_unknown_action(monkeypatch):
    from app.services import agent_tools as at_mod

    fake_project = MagicMock(tenant_id=42, owner_id=42, setup_stage="ready")
    fake_object = MagicMock(id=10)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = fake_project

    class FakeStore:
        def __init__(self, _db):
            pass
        def get_object(self, tenant_id, name):
            return fake_object

    monkeypatch.setattr(at_mod, "OntologyStore", FakeStore)

    toolkit = AgentToolkit(omaha_service=MagicMock(), project_id=1, session_id=2, db=db)
    result = toolkit.execute_tool("edit_ontology", {
        "action": "fly_to_moon",
        "object_name": "订单",
    })
    assert result["success"] is False
    assert "action" in result["error"].lower()
