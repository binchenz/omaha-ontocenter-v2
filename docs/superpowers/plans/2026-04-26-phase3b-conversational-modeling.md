# Phase 3b: Conversational Modeling Enhancement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the existing scan/infer/confirm flow into Agent conversation, add a retail industry template, and let users edit confirmed ontologies via a unified `edit_ontology` tool.

**Architecture:** Five new agent tools (`load_template`, `scan_tables`, `infer_ontology`, `confirm_ontology`, `edit_ontology`) thinly wrap existing services. Drafts persist as pickle files scoped by `(project_id, session_id)`. Templates live in `configs/templates/*.yaml` and are merged into LLM inference via a code-layer back-fill of semantic types. A new `OntologyConfirmPanel` frontend component renders the inferred draft via the existing `panel_type: ontology_preview` mechanism.

**Tech Stack:** FastAPI, SQLAlchemy, pandas, PyYAML, React 18 + TypeScript + Tailwind.

---

## File Structure

### Backend — New Files
- `backend/app/services/ontology_draft_store.py` — pickle-based draft persistence (project+session scoped)
- `backend/app/services/template_loader.py` — loads `configs/templates/*.yaml`
- `configs/templates/retail.yaml` — retail industry template (订单/客户/库存/商品)
- `backend/tests/test_ontology_draft_store.py`
- `backend/tests/test_template_loader.py`
- `backend/tests/test_ontology_inferrer_template.py`
- `backend/tests/test_phase3b_tools.py` — 5 new agent tools
- `backend/tests/test_modeling_flow.py` — integration test

### Backend — Modified Files
- `backend/app/services/ontology_inferrer.py` — accept `template_hint`, add `compact_template`, `merge_template_semantic_types`
- `backend/app/services/agent_tools.py` — add 5 tools
- `backend/app/services/chat.py` — register 5 tool schemas, dispatch in `_execute_tool`, advance `setup_stage` after `clean_data`/`confirm_ontology`
- `backend/app/schemas/structured_response.py` — extend `panel_type` Literal to include `ontology_preview`

### Frontend — New Files
- `frontend/src/components/chat/OntologyConfirmPanel.tsx`

### Frontend — Modified Files
- `frontend/src/components/chat/StructuredMessage.tsx` — dispatch new panel_type

---

### Task 1: OntologyDraftStore

**Files:**
- Create: `backend/app/services/ontology_draft_store.py`
- Create: `backend/tests/test_ontology_draft_store.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_ontology_draft_store.py
import pytest
from app.services.ontology_draft_store import OntologyDraftStore


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


def test_load_when_missing_returns_none():
    assert OntologyDraftStore.load(1, 2) is None


def test_save_and_load_roundtrip():
    OntologyDraftStore.save(
        project_id=1, session_id=2,
        objects=[{"name": "订单"}],
        relationships=[{"from": "订单", "to": "客户"}],
        warnings=["test warning"],
    )
    loaded = OntologyDraftStore.load(1, 2)
    assert loaded is not None
    assert loaded["objects"] == [{"name": "订单"}]
    assert loaded["relationships"] == [{"from": "订单", "to": "客户"}]
    assert loaded["warnings"] == ["test warning"]


def test_save_overwrites_existing():
    OntologyDraftStore.save(1, 2, [{"name": "old"}], [], [])
    OntologyDraftStore.save(1, 2, [{"name": "new"}], [], [])
    assert OntologyDraftStore.load(1, 2)["objects"] == [{"name": "new"}]


def test_clear_removes_draft():
    OntologyDraftStore.save(1, 2, [{"name": "x"}], [], [])
    OntologyDraftStore.clear(1, 2)
    assert OntologyDraftStore.load(1, 2) is None


def test_clear_when_missing_does_not_raise():
    OntologyDraftStore.clear(99, 99)


def test_isolation_between_sessions():
    OntologyDraftStore.save(1, 2, [{"name": "a"}], [], [])
    OntologyDraftStore.save(1, 3, [{"name": "b"}], [], [])
    assert OntologyDraftStore.load(1, 2)["objects"] == [{"name": "a"}]
    assert OntologyDraftStore.load(1, 3)["objects"] == [{"name": "b"}]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/.worktrees/phase3b-modeling/backend
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_ontology_draft_store.py -v
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement OntologyDraftStore**

```python
# backend/app/services/ontology_draft_store.py
"""Pickle-based ontology draft storage scoped by (project_id, session_id)."""
import pickle
from pathlib import Path


_BASE = Path("data/uploads")


def _draft_dir(project_id: int, session_id: int) -> Path:
    return (_BASE / str(project_id) / str(session_id) / "_drafts").resolve()


def _draft_path(project_id: int, session_id: int) -> Path:
    return _draft_dir(project_id, session_id) / "draft.pkl"


class OntologyDraftStore:
    @staticmethod
    def save(
        project_id: int,
        session_id: int,
        objects: list,
        relationships: list,
        warnings: list,
    ) -> None:
        d = _draft_dir(project_id, session_id)
        d.mkdir(parents=True, exist_ok=True)
        payload = {
            "objects": objects,
            "relationships": relationships,
            "warnings": warnings,
        }
        with _draft_path(project_id, session_id).open("wb") as f:
            pickle.dump(payload, f)

    @staticmethod
    def load(project_id: int, session_id: int) -> dict | None:
        p = _draft_path(project_id, session_id)
        if not p.exists():
            return None
        with p.open("rb") as f:
            return pickle.load(f)

    @staticmethod
    def clear(project_id: int, session_id: int) -> None:
        p = _draft_path(project_id, session_id)
        if p.exists():
            p.unlink()
```

- [ ] **Step 4: Run tests to verify pass**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_ontology_draft_store.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ontology_draft_store.py backend/tests/test_ontology_draft_store.py
git commit -m "feat: add OntologyDraftStore for session-scoped pickle drafts"
```

---

### Task 2: Retail Industry Template

**Files:**
- Create: `configs/templates/retail.yaml`

- [ ] **Step 1: Create the retail template**

```yaml
# configs/templates/retail.yaml
industry: retail
display_name: 零售/电商
domain: retail
objects:
  - name: 订单
    description: 客户的采购订单
    business_context: 从下单到签收的全生命周期
    properties:
      - name: 订单号
        data_type: string
        semantic_type: order_id
      - name: 客户ID
        data_type: string
        semantic_type: customer_id
      - name: 金额
        data_type: number
        semantic_type: currency_cny
      - name: 状态
        data_type: string
        semantic_type: order_status
      - name: 下单时间
        data_type: datetime
        semantic_type: datetime

  - name: 客户
    description: 客户档案
    business_context: 客户基本信息与联系方式
    properties:
      - name: ID
        data_type: string
        semantic_type: customer_id
      - name: 客户名
        data_type: string
        semantic_type: person_name
      - name: 电话
        data_type: string
        semantic_type: phone
      - name: 地区
        data_type: string
        semantic_type: region

  - name: 库存
    description: 商品库存
    business_context: 各仓库的商品数量与成本
    properties:
      - name: 商品ID
        data_type: string
        semantic_type: product_id
      - name: 商品名
        data_type: string
        semantic_type: product_name
      - name: 数量
        data_type: number
        semantic_type: quantity
      - name: 成本
        data_type: number
        semantic_type: currency_cny

  - name: 商品
    description: 商品档案
    business_context: 商品基本信息
    properties:
      - name: ID
        data_type: string
        semantic_type: product_id
      - name: 名称
        data_type: string
        semantic_type: product_name
      - name: 分类
        data_type: string
        semantic_type: category
      - name: 售价
        data_type: number
        semantic_type: currency_cny

relationships:
  - from: 订单
    to: 客户
    type: belongs_to
    from_field: 客户ID
    to_field: ID
  - from: 库存
    to: 商品
    type: belongs_to
    from_field: 商品ID
    to_field: ID
```

- [ ] **Step 2: Verify YAML parses**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -c "import yaml; t = yaml.safe_load(open('configs/templates/retail.yaml')); print(t['industry'], len(t['objects']), 'objects')"
```
Expected: `retail 4 objects`

- [ ] **Step 3: Commit**

```bash
git add configs/templates/retail.yaml
git commit -m "feat: add retail industry template (订单/客户/库存/商品)"
```

---

### Task 3: TemplateLoader

**Files:**
- Create: `backend/app/services/template_loader.py`
- Create: `backend/tests/test_template_loader.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_template_loader.py
from app.services.template_loader import TemplateLoader


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_template_loader.py -v
```
Expected: FAIL — module not found.

- [ ] **Step 3: Implement TemplateLoader**

```python
# backend/app/services/template_loader.py
"""Loads industry templates from configs/templates/*.yaml."""
from pathlib import Path
import yaml


_TEMPLATE_DIR = Path("configs/templates")


class TemplateLoader:
    @staticmethod
    def list_industries() -> list[dict]:
        result = []
        if not _TEMPLATE_DIR.exists():
            return result
        for yml in sorted(_TEMPLATE_DIR.glob("*.yaml")):
            try:
                data = yaml.safe_load(yml.read_text(encoding="utf-8"))
            except yaml.YAMLError:
                continue
            if not isinstance(data, dict):
                continue
            value = data.get("industry") or yml.stem
            result.append({
                "value": value,
                "display_name": data.get("display_name", value),
                "domain": data.get("domain", value),
            })
        return result

    @staticmethod
    def load(industry: str) -> dict | None:
        path = _TEMPLATE_DIR / f"{industry}.yaml"
        if not path.exists():
            return None
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            return None
        return data if isinstance(data, dict) else None
```

- [ ] **Step 4: Run tests to verify pass**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_template_loader.py -v
```
Expected: 3 passed.

Note: tests run from repo root by default (where `configs/` lives). If pytest is run from `backend/`, the relative path resolves to `backend/configs/templates`, which doesn't exist. Verify pytest cwd matches by running this command from the worktree's `backend/` folder; the `Path("configs/templates")` resolves relative to whatever cwd uvicorn/pytest runs from in production — same convention as existing `data/uploads/` paths.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/template_loader.py backend/tests/test_template_loader.py
git commit -m "feat: add TemplateLoader for industry template YAML files"
```

---

### Task 4: OntologyInferrer template_hint + merge_template_semantic_types

**Files:**
- Modify: `backend/app/services/ontology_inferrer.py`
- Create: `backend/tests/test_ontology_inferrer_template.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_ontology_inferrer_template.py
from app.services.ontology_inferrer import (
    compact_template, merge_template_semantic_types,
)
from app.schemas.auto_model import InferredObject, InferredProperty


RETAIL_TEMPLATE = {
    "industry": "retail",
    "objects": [
        {
            "name": "订单",
            "description": "客户的采购订单",
            "properties": [
                {"name": "订单号", "data_type": "string", "semantic_type": "order_id"},
                {"name": "金额", "data_type": "number", "semantic_type": "currency_cny"},
                {"name": "状态", "data_type": "string", "semantic_type": "order_status"},
            ],
        },
    ],
    "relationships": [],
}


def test_compact_template_drops_semantic_types():
    compact = compact_template(RETAIL_TEMPLATE)
    assert compact["objects"][0]["name"] == "订单"
    assert compact["objects"][0]["description"] == "客户的采购订单"
    assert compact["objects"][0]["field_names"] == ["订单号", "金额", "状态"]
    assert "semantic_type" not in str(compact)


def test_merge_template_back_fills_semantic_types():
    inferred = [
        InferredObject(
            name="订单",
            source_entity="orders",
            datasource_id="ds1",
            datasource_type="csv",
            properties=[
                InferredProperty(name="订单号", data_type="string", semantic_type=None),
                InferredProperty(name="金额", data_type="number", semantic_type="text"),
                InferredProperty(name="状态", data_type="string"),
            ],
        ),
    ]
    merged = merge_template_semantic_types(inferred, RETAIL_TEMPLATE)
    props = {p.name: p.semantic_type for p in merged[0].properties}
    assert props["订单号"] == "order_id"
    assert props["金额"] == "currency_cny"
    assert props["状态"] == "order_status"


def test_merge_skips_unknown_objects():
    inferred = [
        InferredObject(
            name="发票",
            source_entity="invoices",
            datasource_id="ds1",
            datasource_type="csv",
            properties=[
                InferredProperty(name="发票号", data_type="string", semantic_type="invoice_id"),
            ],
        ),
    ]
    merged = merge_template_semantic_types(inferred, RETAIL_TEMPLATE)
    assert merged[0].properties[0].semantic_type == "invoice_id"


def test_merge_keeps_inferred_value_when_field_not_in_template():
    inferred = [
        InferredObject(
            name="订单",
            source_entity="orders",
            datasource_id="ds1",
            datasource_type="csv",
            properties=[
                InferredProperty(name="备注", data_type="string", semantic_type="text"),
            ],
        ),
    ]
    merged = merge_template_semantic_types(inferred, RETAIL_TEMPLATE)
    assert merged[0].properties[0].semantic_type == "text"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_ontology_inferrer_template.py -v
```
Expected: FAIL — `compact_template`/`merge_template_semantic_types` not defined.

- [ ] **Step 3: Add helpers to `ontology_inferrer.py`**

Add these module-level functions at the bottom of `backend/app/services/ontology_inferrer.py`:

```python
def compact_template(template: dict) -> dict:
    """Reduce a template to the minimal hint passed to the LLM.

    Strip semantic_types so the LLM focuses on object/field NAME mapping.
    Code-layer back-fills semantic types after inference.
    """
    return {
        "objects": [
            {
                "name": obj["name"],
                "description": obj.get("description", ""),
                "field_names": [p["name"] for p in obj.get("properties", [])],
            }
            for obj in template.get("objects", [])
        ],
        "relationships": template.get("relationships", []),
    }


def merge_template_semantic_types(inferred, template):
    """Back-fill semantic_types on inferred objects from the template.

    Match logic:
    - If inferred.name == template.object.name, walk inferred properties
    - For each inferred property, look up same-named property in template
    - If template has a semantic_type for that name, overwrite inferred one
    - Otherwise leave inferred value alone
    """
    template_map = {
        obj["name"]: {p["name"]: p.get("semantic_type") for p in obj.get("properties", [])}
        for obj in template.get("objects", [])
    }
    for obj in inferred:
        prop_map = template_map.get(obj.name)
        if not prop_map:
            continue
        for prop in obj.properties:
            tmpl_st = prop_map.get(prop.name)
            if tmpl_st:
                prop.semantic_type = tmpl_st
    return inferred
```

- [ ] **Step 4: Extend `infer_table` to accept template_hint**

Replace the existing `infer_table` body so it appends template hint to the prompt when given:

```python
def infer_table(self, table: TableSummary, datasource_id: str, template_hint: dict | None = None) -> Optional[InferredObject]:
    columns_text = "\n".join(
        f"- {c['name']} ({c['type']}) 样本值: {table.sample_values.get(c['name'], [])[:10]}"
        for c in table.columns
    )
    prompt = INFER_PROMPT.format(
        table_name=table.name,
        row_count=table.row_count,
        columns_text=columns_text,
        semantic_types=", ".join(SEMANTIC_TYPES),
    )
    if template_hint:
        hint_json = json.dumps(template_hint, ensure_ascii=False)
        prompt += (
            f"\n\n参考的行业模板（如适用）：\n{hint_json}\n"
            "如果某张表的字段和模板中的某个对象高度相似（字段名重叠 50% 以上），"
            "请在输出 JSON 的 name 字段使用模板中的对象名。"
            "如果不匹配，按你的最佳判断推断。"
        )
    for attempt in range(settings.INFER_MAX_RETRIES + 1):
        try:
            raw = self._call_llm(prompt)
            parsed = self._extract_json(raw)
            if not isinstance(parsed, dict):
                continue
            parsed.setdefault("datasource_id", datasource_id)
            parsed.setdefault("datasource_type", "sql")
            obj = InferredObject.model_validate(parsed)
            return self._validate_semantic_types(obj)
        except Exception:
            continue
    return None
```

- [ ] **Step 5: Run tests + verify regression-free**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_ontology_inferrer_template.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ontology_inferrer.py backend/tests/test_ontology_inferrer_template.py
git commit -m "feat: add template_hint + merge helpers to OntologyInferrer"
```

---

### Task 5: AgentToolkit — load_template + scan_tables

**Files:**
- Modify: `backend/app/services/agent_tools.py`
- Create: `backend/tests/test_phase3b_tools.py` (initial scaffold for all 5 new tools — extended in later tasks)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_phase3b_tools.py
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
        staticmethod(lambda industry: {"industry": industry, "objects": [{"name": "订单", "properties": []}], "relationships": []})
    )
    result = toolkit.execute_tool("load_template", {"industry": "retail"})
    assert result["success"] is True
    assert result["data"]["display_name"] or result["data"]["objects"]


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
    column_names = [c["name"] for c in table["columns"]]
    assert "客户" in column_names
    assert "sample_values" in table


def test_scan_tables_no_uploaded_data(toolkit):
    result = toolkit.execute_tool("scan_tables", {})
    assert result["success"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_phase3b_tools.py -v
```
Expected: FAIL — tools not registered.

- [ ] **Step 3: Add tools to AgentToolkit**

In `backend/app/services/agent_tools.py`, register handlers in `__init__` `self._tools` dict:

```python
"load_template": self._load_template,
"scan_tables": self._scan_tables,
```

In `get_tool_definitions()` append:

```python
{
    "name": "load_template",
    "description": "加载行业模板，返回该行业典型的业务对象定义。在用户告知行业后调用，结果可作为 infer_ontology 的先验。",
    "parameters": {
        "industry": {"type": "string", "description": "行业代码：retail / manufacturing / trade / service", "required": True}
    }
},
{
    "name": "scan_tables",
    "description": "扫描已上传的数据表，返回每张表的列、行数和样本值。在准备建模前调用。",
    "parameters": {}
},
```

Add handler methods on the class:

```python
def _load_template(self, params: dict) -> dict:
    from app.services.template_loader import TemplateLoader
    industry = params.get("industry")
    if not industry:
        return {"success": False, "error": "industry 参数必填"}
    template = TemplateLoader.load(industry)
    if not template:
        return {"success": False, "error": f"未知行业模板: {industry}"}
    return {
        "success": True,
        "data": {
            "industry": template.get("industry", industry),
            "display_name": template.get("display_name", industry),
            "domain": template.get("domain", industry),
            "objects": template.get("objects", []),
            "relationships": template.get("relationships", []),
        }
    }

def _scan_tables(self, params: dict) -> dict:
    tables = self._load_tables()
    if not tables:
        return {"success": False, "error": "没有已上传的数据，请先上传文件"}
    summaries = []
    for name, df in tables.items():
        summaries.append({
            "name": name,
            "row_count": int(len(df)),
            "columns": [{"name": str(c), "type": str(df[c].dtype)} for c in df.columns],
            "sample_values": {
                str(c): [str(v) for v in df[c].dropna().astype(str).head(20).tolist()]
                for c in df.columns
            },
        })
    return {"success": True, "data": {"tables": summaries}}
```

- [ ] **Step 4: Run tests to verify pass**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_phase3b_tools.py -v
```
Expected: 4 passed (or however many of the four tasks 5/6/7/8 tests are present at this point — only the load_template + scan_tables tests should pass; the others fail until later tasks add handlers).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent_tools.py backend/tests/test_phase3b_tools.py
git commit -m "feat: add load_template and scan_tables agent tools"
```

---

### Task 6: AgentToolkit — infer_ontology

**Files:**
- Modify: `backend/app/services/agent_tools.py`
- Modify: `backend/tests/test_phase3b_tools.py` (append tests)

- [ ] **Step 1: Append failing tests**

Append to `backend/tests/test_phase3b_tools.py`:

```python
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
            InferredProperty(name="客户", data_type="string", semantic_type="customer_id"),
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

    toolkit.execute_tool("infer_ontology", {})
    draft = OntologyDraftStore.load(1, 2)
    assert draft["objects"][0]["name"] == "新对象"


def test_infer_ontology_no_uploaded_data(toolkit):
    result = toolkit.execute_tool("infer_ontology", {})
    assert result["success"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_phase3b_tools.py -v
```
Expected: 3 new tests fail.

- [ ] **Step 3: Register `infer_ontology` in AgentToolkit**

In `__init__` `self._tools` dict add:

```python
"infer_ontology": self._infer_ontology,
```

In `get_tool_definitions()` append:

```python
{
    "name": "infer_ontology",
    "description": "基于已上传数据 + 可选行业模板，调 LLM 推断本体（业务对象、字段语义、关系）。结果存为草稿，用户确认后才生效。如果已有草稿会被覆盖。",
    "parameters": {
        "industry": {
            "type": "string",
            "description": "行业代码（可选）。如有值，会先加载对应模板作为 LLM 提示",
            "required": False
        }
    }
},
```

Add the handler:

```python
def _infer_ontology(self, params: dict) -> dict:
    from app.services.ontology_inferrer import (
        OntologyInferrer, compact_template, merge_template_semantic_types,
    )
    from app.services.ontology_draft_store import OntologyDraftStore
    from app.services.template_loader import TemplateLoader
    from app.services.schema_scanner import TableSummary

    if self.project_id is None or self.session_id is None:
        return {"success": False, "error": "project_id/session_id missing on toolkit"}

    tables = self._load_tables()
    if not tables:
        return {"success": False, "error": "没有已上传的数据，请先上传文件"}

    template = None
    template_hint = None
    industry = params.get("industry")
    if industry:
        template = TemplateLoader.load(industry)
        if template:
            template_hint = compact_template(template)

    inferrer = OntologyInferrer()
    inferred_objects = []
    warnings: list[str] = []
    for name, df in tables.items():
        summary = TableSummary(
            name=name,
            row_count=int(len(df)),
            columns=[{"name": str(c), "type": str(df[c].dtype), "nullable": True} for c in df.columns],
            sample_values={
                str(c): [str(v) for v in df[c].dropna().astype(str).head(20).tolist()]
                for c in df.columns
            },
        )
        try:
            obj = inferrer.infer_table(summary, datasource_id="upload", template_hint=template_hint)
        except Exception as e:
            warnings.append(f"{name}: 推断失败 ({e})")
            continue
        if obj is None:
            warnings.append(f"{name}: LLM 未返回有效结果")
            continue
        inferred_objects.append(obj)

    if template:
        inferred_objects = merge_template_semantic_types(inferred_objects, template)

    relationships = inferrer.infer_relationships_by_naming(inferred_objects)

    OntologyDraftStore.save(
        project_id=self.project_id,
        session_id=self.session_id,
        objects=[obj.model_dump() for obj in inferred_objects],
        relationships=[rel.model_dump() for rel in relationships],
        warnings=warnings,
    )

    return {
        "success": True,
        "data": {
            "objects_count": len(inferred_objects),
            "relationships_count": len(relationships),
            "warnings": warnings,
            "objects": [obj.model_dump() for obj in inferred_objects],
            "relationships": [rel.model_dump() for rel in relationships],
            "template_name": template.get("display_name") if template else None,
        }
    }
```

- [ ] **Step 4: Run tests to verify pass**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_phase3b_tools.py -v
```
Expected: previous 4 + 3 new = 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent_tools.py backend/tests/test_phase3b_tools.py
git commit -m "feat: add infer_ontology agent tool with draft + template support"
```

---

### Task 7: AgentToolkit — confirm_ontology

**Files:**
- Modify: `backend/app/services/agent_tools.py`
- Modify: `backend/tests/test_phase3b_tools.py`

This tool is more involved because it needs DB access. The toolkit doesn't currently hold a `db` session — it only holds `omaha_service`. We add a `db` parameter to the toolkit constructor (None default for backward compat) and wire it from `ChatService._execute_tool` in Task 9.

- [ ] **Step 1: Append failing tests**

```python
def test_confirm_ontology_persists_draft_and_clears(monkeypatch):
    from app.services.ontology_draft_store import OntologyDraftStore
    from app.services.agent_tools import AgentToolkit

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

    monkeypatch.setattr(at_mod, "OntologyImporter", FakeImporter, raising=False)

    toolkit = AgentToolkit(omaha_service=MagicMock(), project_id=1, session_id=2, db=db)
    result = toolkit.execute_tool("confirm_ontology", {})

    assert result["success"] is True
    assert result["data"]["objects_created"] == 1
    assert imported["tenant_id"] == 42
    assert OntologyDraftStore.load(1, 2) is None
    assert fake_project.setup_stage == "ready"
    db.commit.assert_called()


def test_confirm_ontology_no_draft():
    from app.services.agent_tools import AgentToolkit
    db = MagicMock()
    toolkit = AgentToolkit(omaha_service=MagicMock(), project_id=99, session_id=99, db=db)
    result = toolkit.execute_tool("confirm_ontology", {})
    assert result["success"] is False
    assert "draft" in result["error"].lower() or "草稿" in result["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_phase3b_tools.py -v
```
Expected: 2 new tests fail.

- [ ] **Step 3: Add `db` parameter to AgentToolkit + register confirm tool**

In `backend/app/services/agent_tools.py`:

Update imports at top of file:

```python
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
```

Add a module-level import binding so tests can monkeypatch it:

```python
from app.services.ontology_importer import OntologyImporter
```

Update `__init__` signature:

```python
def __init__(
    self,
    omaha_service,
    ontology_context: Dict = None,
    project_id: Optional[int] = None,
    session_id: Optional[int] = None,
    db: Optional[Session] = None,
):
    self.omaha_service = omaha_service
    self.ontology_context = ontology_context or {}
    self.project_id = project_id
    self.session_id = session_id
    self.db = db
    self._uploaded_tables: Dict = {}
    self._tools = {
        # existing entries unchanged
        "query_data": self._query_data,
        "list_objects": self._list_objects,
        "get_schema": self._get_schema,
        "generate_chart": self._generate_chart,
        "upload_file": self._upload_file,
        "assess_quality": self._assess_quality,
        "clean_data": self._clean_data,
        "load_template": self._load_template,
        "scan_tables": self._scan_tables,
        "infer_ontology": self._infer_ontology,
        "confirm_ontology": self._confirm_ontology,
    }
```

Append to `get_tool_definitions()`:

```python
{
    "name": "confirm_ontology",
    "description": "用户确认建模草稿后调用。把草稿持久化到本体库，setup_stage 推到 ready。如无草稿则报错。",
    "parameters": {}
},
```

Add the handler:

```python
def _confirm_ontology(self, params: dict) -> dict:
    from app.services.ontology_draft_store import OntologyDraftStore
    from app.models.project import Project

    if self.project_id is None or self.session_id is None:
        return {"success": False, "error": "project_id/session_id missing on toolkit"}
    if self.db is None:
        return {"success": False, "error": "db session missing on toolkit"}

    draft = OntologyDraftStore.load(self.project_id, self.session_id)
    if not draft or not draft.get("objects"):
        return {"success": False, "error": "没有可确认的草稿，请先调用 infer_ontology"}

    project = self.db.query(Project).filter(Project.id == self.project_id).first()
    if not project:
        return {"success": False, "error": f"project {self.project_id} not found"}

    tenant_id = project.tenant_id or project.owner_id

    config = {
        "datasources": [{"id": "upload", "type": "csv"}],
        "ontology": {
            "objects": [
                {
                    "name": obj["name"],
                    "datasource": obj.get("datasource_id", "upload"),
                    "source_entity": obj.get("source_entity", obj["name"]),
                    "description": obj.get("description"),
                    "business_context": obj.get("business_context"),
                    "domain": obj.get("domain"),
                    "properties": [
                        {
                            "name": p["name"],
                            "type": p.get("data_type", "string"),
                            "semantic_type": p.get("semantic_type"),
                            "description": p.get("description"),
                        }
                        for p in obj.get("properties", [])
                    ],
                }
                for obj in draft["objects"]
            ],
        },
    }

    importer = OntologyImporter(self.db)
    result = importer.import_dict(tenant_id, config)

    project.setup_stage = "ready"
    self.db.commit()

    OntologyDraftStore.clear(self.project_id, self.session_id)

    return {
        "success": True,
        "data": {
            "objects_created": result.get("objects_created", 0),
            "objects_updated": result.get("objects_updated", 0),
            "relationships_created": result.get("relationships_created", 0),
        }
    }
```

- [ ] **Step 4: Run tests**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_phase3b_tools.py -v
```
Expected: All 9 phase3b tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent_tools.py backend/tests/test_phase3b_tools.py
git commit -m "feat: add confirm_ontology tool that persists draft and advances setup_stage"
```

---

### Task 8: AgentToolkit — edit_ontology

**Files:**
- Modify: `backend/app/services/agent_tools.py`
- Modify: `backend/tests/test_phase3b_tools.py`

`edit_ontology` requires `setup_stage == "ready"`. It supports 8 actions on confirmed ontology objects.

- [ ] **Step 1: Append failing tests**

```python
def test_edit_ontology_blocks_non_ready_stage(monkeypatch):
    from app.services.agent_tools import AgentToolkit
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
    from app.services.agent_tools import AgentToolkit
    from app.services import agent_tools as at_mod

    fake_project = MagicMock(tenant_id=42, owner_id=42, setup_stage="ready")
    fake_object = MagicMock(id=10, name="订单")
    fake_property = MagicMock(name="金额", id=20)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [fake_project]

    class FakeStore:
        def __init__(self, _db):
            self.calls = []
        def get_object(self, tenant_id, name):
            return fake_object
        def rename_property(self, object_id, old_name, new_name):
            self.calls.append(("rename_property", object_id, old_name, new_name))
            return True

    fake_store = FakeStore(db)
    monkeypatch.setattr(at_mod, "OntologyStore", lambda _db: fake_store)

    toolkit = AgentToolkit(omaha_service=MagicMock(), project_id=1, session_id=2, db=db)
    result = toolkit.execute_tool("edit_ontology", {
        "action": "rename_property",
        "object_name": "订单",
        "property_name": "金额",
        "new_value": "总金额",
    })
    assert result["success"] is True
    assert ("rename_property", 10, "金额", "总金额") in fake_store.calls


def test_edit_ontology_unknown_action(monkeypatch):
    from app.services.agent_tools import AgentToolkit
    fake_project = MagicMock(tenant_id=42, owner_id=42, setup_stage="ready")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = fake_project
    toolkit = AgentToolkit(omaha_service=MagicMock(), project_id=1, session_id=2, db=db)
    result = toolkit.execute_tool("edit_ontology", {
        "action": "fly_to_moon",
        "object_name": "订单",
    })
    assert result["success"] is False
    assert "action" in result["error"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_phase3b_tools.py -v
```
Expected: 3 new tests fail.

- [ ] **Step 3: Extend OntologyStore with the missing edit methods**

The existing `OntologyStore` has `create_*` / `add_*` / `delete_object` but no rename or update helpers. Add them at the bottom of `backend/app/services/ontology_store.py` class body:

```python
def rename_object(self, tenant_id: int, old_name: str, new_name: str) -> bool:
    obj = self.get_object(tenant_id, old_name)
    if obj is None:
        return False
    obj.name = new_name
    self.db.flush()
    return True

def update_object_description(self, tenant_id: int, name: str, description: str) -> bool:
    obj = self.get_object(tenant_id, name)
    if obj is None:
        return False
    obj.description = description
    self.db.flush()
    return True

def rename_property(self, object_id: int, old_name: str, new_name: str) -> bool:
    from app.models.ontology import ObjectProperty
    prop = self.db.query(ObjectProperty).filter(
        ObjectProperty.object_id == object_id,
        ObjectProperty.name == old_name,
    ).first()
    if prop is None:
        return False
    prop.name = new_name
    self.db.flush()
    return True

def update_property_semantic_type(self, object_id: int, name: str, semantic_type: str | None) -> bool:
    from app.models.ontology import ObjectProperty
    prop = self.db.query(ObjectProperty).filter(
        ObjectProperty.object_id == object_id,
        ObjectProperty.name == name,
    ).first()
    if prop is None:
        return False
    prop.semantic_type = semantic_type
    self.db.flush()
    return True

def update_property_description(self, object_id: int, name: str, description: str) -> bool:
    from app.models.ontology import ObjectProperty
    prop = self.db.query(ObjectProperty).filter(
        ObjectProperty.object_id == object_id,
        ObjectProperty.name == name,
    ).first()
    if prop is None:
        return False
    prop.description = description
    self.db.flush()
    return True

def remove_property(self, object_id: int, name: str) -> bool:
    from app.models.ontology import ObjectProperty
    prop = self.db.query(ObjectProperty).filter(
        ObjectProperty.object_id == object_id,
        ObjectProperty.name == name,
    ).first()
    if prop is None:
        return False
    self.db.delete(prop)
    self.db.flush()
    return True

def remove_relationship(self, tenant_id: int, name: str) -> bool:
    from app.models.ontology import OntologyRelationship
    rel = self.db.query(OntologyRelationship).filter(
        OntologyRelationship.tenant_id == tenant_id,
        OntologyRelationship.name == name,
    ).first()
    if rel is None:
        return False
    self.db.delete(rel)
    self.db.flush()
    return True
```

- [ ] **Step 4: Register `edit_ontology` in AgentToolkit**

Module-level import at top of `agent_tools.py`:

```python
from app.services.ontology_store import OntologyStore
```

In `__init__` `self._tools` dict add:

```python
"edit_ontology": self._edit_ontology,
```

In `get_tool_definitions()` append:

```python
{
    "name": "edit_ontology",
    "description": "修改已确认的本体（重命名对象/字段、改语义类型、增删字段或关系）。setup_stage 必须为 ready 才能调用。",
    "parameters": {
        "action": {
            "type": "string",
            "description": "rename_object | rename_property | change_semantic_type | update_description | add_property | remove_property | add_relationship | remove_relationship",
            "required": True
        },
        "object_name": {"type": "string", "required": True},
        "property_name": {"type": "string", "required": False},
        "new_value": {"type": "string", "required": False},
        "data_type": {"type": "string", "required": False},
        "semantic_type": {"type": "string", "required": False},
        "to_object": {"type": "string", "required": False},
        "from_field": {"type": "string", "required": False},
        "to_field": {"type": "string", "required": False},
    }
},
```

Add the handler:

```python
def _edit_ontology(self, params: dict) -> dict:
    from app.models.project import Project

    if self.project_id is None or self.db is None:
        return {"success": False, "error": "project_id/db missing on toolkit"}

    project = self.db.query(Project).filter(Project.id == self.project_id).first()
    if not project:
        return {"success": False, "error": f"project {self.project_id} not found"}
    if project.setup_stage != "ready":
        return {"success": False, "error": "edit_ontology 仅在已确认本体后可用 (setup_stage=ready)"}

    tenant_id = project.tenant_id or project.owner_id
    store = OntologyStore(self.db)

    action = params.get("action")
    object_name = params.get("object_name")
    if not action or not object_name:
        return {"success": False, "error": "action 和 object_name 必填"}

    obj = store.get_object(tenant_id, object_name)
    if obj is None and action != "add_relationship":
        return {"success": False, "error": f"未找到对象: {object_name}"}

    try:
        if action == "rename_object":
            ok = store.rename_object(tenant_id, object_name, params["new_value"])
        elif action == "rename_property":
            ok = store.rename_property(obj.id, params["property_name"], params["new_value"])
        elif action == "change_semantic_type":
            ok = store.update_property_semantic_type(obj.id, params["property_name"], params["new_value"])
        elif action == "update_description":
            if params.get("property_name"):
                ok = store.update_property_description(obj.id, params["property_name"], params["new_value"])
            else:
                ok = store.update_object_description(tenant_id, object_name, params["new_value"])
        elif action == "add_property":
            store.add_property(
                object_id=obj.id,
                name=params["property_name"],
                data_type=params.get("data_type", "string"),
                semantic_type=params.get("semantic_type"),
            )
            ok = True
        elif action == "remove_property":
            ok = store.remove_property(obj.id, params["property_name"])
        elif action == "add_relationship":
            to_obj = store.get_object(tenant_id, params["to_object"])
            if not to_obj:
                return {"success": False, "error": f"未找到目标对象: {params['to_object']}"}
            store.add_relationship(
                tenant_id=tenant_id,
                name=f"{object_name}_{params['to_object']}",
                from_object_id=obj.id if obj else None,
                to_object_id=to_obj.id,
                relationship_type="belongs_to",
                from_field=params["from_field"],
                to_field=params["to_field"],
            )
            ok = True
        elif action == "remove_relationship":
            ok = store.remove_relationship(tenant_id, params.get("new_value") or object_name)
        else:
            return {"success": False, "error": f"未知 action: {action}"}

        if not ok:
            return {"success": False, "error": f"操作失败: {action}"}

        self.db.commit()
        return {"success": True, "data": {"action": action, "object_name": object_name}}

    except Exception as e:
        self.db.rollback()
        return {"success": False, "error": f"操作异常: {e}"}
```

- [ ] **Step 5: Run tests**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_phase3b_tools.py tests/test_ontology_inferrer_template.py tests/test_template_loader.py tests/test_ontology_draft_store.py -v
```
Expected: all pass (12 phase3b tool tests + earlier ones).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent_tools.py backend/app/services/ontology_store.py backend/tests/test_phase3b_tools.py
git commit -m "feat: add edit_ontology tool + OntologyStore edit helpers"
```

---

### Task 9: ChatService Wires + setup_stage Advancement

**Files:**
- Modify: `backend/app/services/chat.py`
- Modify: `backend/tests/test_chat_service.py`

ChatService dispatches tools via `_execute_tool` and exposes schemas via `_get_tool_schemas`. Phase 3a wired `assess_quality` and `clean_data`; this task adds the 5 phase 3b tools and advances `setup_stage` automatically when `clean_data` and `confirm_ontology` succeed.

- [ ] **Step 1: Update test_get_tool_schemas count assertion**

In `backend/tests/test_chat_service.py` find:

```python
assert len(tools) == 10
```

Change to:

```python
assert len(tools) == 15
tool_names = [t["function"]["name"] for t in tools]
assert "load_template" in tool_names
assert "scan_tables" in tool_names
assert "infer_ontology" in tool_names
assert "confirm_ontology" in tool_names
assert "edit_ontology" in tool_names
```

- [ ] **Step 2: Run test to verify it fails**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_chat_service.py::test_get_tool_schemas -v
```
Expected: FAIL with `assert 10 == 15`.

- [ ] **Step 3: Append 5 tool schemas in `_get_tool_schemas`**

In `backend/app/services/chat.py`, find the closing bracket of the existing tool list (after the `clean_data` schema) and append before the `]`:

```python
{
    "type": "function",
    "function": {
        "name": "load_template",
        "description": "加载行业模板，返回该行业典型的业务对象定义。在用户告知行业后调用，结果可作为 infer_ontology 的先验。",
        "parameters": {
            "type": "object",
            "properties": {
                "industry": {"type": "string", "description": "行业代码：retail / manufacturing / trade / service"}
            },
            "required": ["industry"]
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "scan_tables",
        "description": "扫描已上传的数据表，返回每张表的列、行数和样本值。在准备建模前调用。",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
},
{
    "type": "function",
    "function": {
        "name": "infer_ontology",
        "description": "基于已上传数据 + 可选行业模板，调 LLM 推断本体。结果存为草稿，用户确认后才生效。",
        "parameters": {
            "type": "object",
            "properties": {
                "industry": {"type": "string", "description": "行业代码（可选）"}
            },
            "required": []
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "confirm_ontology",
        "description": "用户确认建模草稿后调用。把草稿持久化到本体库，setup_stage 推到 ready。",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
},
{
    "type": "function",
    "function": {
        "name": "edit_ontology",
        "description": "修改已确认的本体。setup_stage 必须为 ready 才能调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "rename_object|rename_property|change_semantic_type|update_description|add_property|remove_property|add_relationship|remove_relationship"},
                "object_name": {"type": "string"},
                "property_name": {"type": "string"},
                "new_value": {"type": "string"},
                "data_type": {"type": "string"},
                "semantic_type": {"type": "string"},
                "to_object": {"type": "string"},
                "from_field": {"type": "string"},
                "to_field": {"type": "string"}
            },
            "required": ["action", "object_name"]
        }
    }
}
```

- [ ] **Step 4: Update `_execute_tool` dispatch**

Find the existing `assess_quality / clean_data` branch in `_execute_tool`:

```python
elif tool_name in ("assess_quality", "clean_data"):
    from app.services.agent_tools import AgentToolkit
    toolkit = AgentToolkit(
        omaha_service=None,
        project_id=self.project_id,
        session_id=getattr(self, "_current_session_id", None),
    )
    return toolkit.execute_tool(tool_name, tool_args)
```

Replace with:

```python
elif tool_name in (
    "assess_quality", "clean_data",
    "load_template", "scan_tables",
    "infer_ontology", "confirm_ontology", "edit_ontology",
):
    from app.services.agent_tools import AgentToolkit
    toolkit = AgentToolkit(
        omaha_service=None,
        project_id=self.project_id,
        session_id=getattr(self, "_current_session_id", None),
        db=self.db,
    )
    result = toolkit.execute_tool(tool_name, tool_args)
    if result.get("success"):
        self._advance_setup_stage_for_tool(tool_name)
    return result
```

Add a new method on `ChatService`:

```python
def _advance_setup_stage_for_tool(self, tool_name: str) -> None:
    """Advance project.setup_stage based on tool that just succeeded."""
    if not self.project:
        return
    transitions = {
        "clean_data": ("cleaning", "modeling"),
        # confirm_ontology already sets setup_stage=ready inside the toolkit
    }
    pair = transitions.get(tool_name)
    if not pair:
        return
    expected, next_stage = pair
    if self.project.setup_stage == expected:
        self.project.setup_stage = next_stage
        self.db.commit()
```

- [ ] **Step 5: Run tests**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_chat_service.py -v
```
Expected: pass for `test_get_tool_schemas`. Other tests unchanged.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/chat.py backend/tests/test_chat_service.py
git commit -m "feat: register Phase 3b tools in ChatService + auto-advance setup_stage"
```

---

### Task 10: SYSTEM_TEMPLATE additions

**Files:**
- Modify: `backend/app/services/chat.py`

- [ ] **Step 1: Extend SYSTEM_TEMPLATE workflow tools section**

In `backend/app/services/chat.py`, find the workflow tools section (around line 91, "## 工作流工具（按使用阶段）") and replace the section with:

```
## 工作流工具（按使用阶段）

**接入阶段**
- upload_file: 用户上传文件后系统自动触发（不要主动调用）
- list_datasources: 列出已接入的数据源

**清洗阶段**
- assess_quality: 评估数据质量，返回评分和问题清单
- clean_data: 执行清洗（rules: duplicate_rows / strip_whitespace / standardize_dates）

**建模阶段**
- load_template: 加载行业模板（用户告知行业后调用）
- scan_tables: 扫描已上传数据
- infer_ontology: LLM 推断业务对象 + 字段语义 + 关系（结果写草稿，可传 industry 参数复用模板）
- confirm_ontology: 持久化草稿到本体库
- edit_ontology: 修改已确认的本体（仅 setup_stage=ready 时可用）

**查询阶段**
- list_objects: 列出所有业务对象
- get_schema: 获取对象的字段定义
- query_data: 查询业务数据
- generate_chart: 生成图表
```

- [ ] **Step 2: Append `ontology_preview` panel example**

In the same file, find the structured富组件输出 section. The current quality_report example is shown with double-braced JSON. After the quality_report example, add:

````
**展示建模草稿（infer_ontology 工具返回后，必须用此格式展示）：**
```structured
{{"type": "panel", "panel_type": "ontology_preview", "content": "我识别出这些业务对象，请确认", "data": {{"template_name": "零售/电商", "objects": [...], "relationships": [...], "warnings": [...]}}}}
```
````

The `data` field should be the entire `data` object returned by `infer_ontology`.

- [ ] **Step 3: Run regression**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_chat_service.py tests/test_extract_structured.py -v
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/chat.py
git commit -m "feat: extend SYSTEM_TEMPLATE with modeling stage tools and ontology_preview example"
```

---

### Task 11: Frontend OntologyConfirmPanel

**Files:**
- Create: `frontend/src/components/chat/OntologyConfirmPanel.tsx`
- Modify: `frontend/src/components/chat/StructuredMessage.tsx`
- Modify: `backend/app/schemas/structured_response.py`

- [ ] **Step 1: Extend backend Pydantic literal**

In `backend/app/schemas/structured_response.py` find:

```python
class PanelResponse(BaseModel):
    type: Literal["panel"] = "panel"
    content: str
    panel_type: Literal["quality_report"]
    data: dict[str, Any]
```

Change to:

```python
class PanelResponse(BaseModel):
    type: Literal["panel"] = "panel"
    content: str
    panel_type: Literal["quality_report", "ontology_preview"]
    data: dict[str, Any]
```

- [ ] **Step 2: Run backend regression**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_structured_response.py -v
```
Expected: pass.

- [ ] **Step 3: Implement OntologyConfirmPanel**

```tsx
// frontend/src/components/chat/OntologyConfirmPanel.tsx
import { useState } from 'react';

interface InferredProperty {
  name: string;
  data_type: string;
  semantic_type?: string | null;
  description?: string | null;
}

interface InferredObject {
  name: string;
  source_entity?: string;
  description?: string | null;
  business_context?: string | null;
  properties: InferredProperty[];
}

interface InferredRelationship {
  name?: string;
  from_object: string;
  to_object: string;
  from_field: string;
  to_field: string;
}

interface OntologyPreviewData {
  template_name?: string | null;
  objects: InferredObject[];
  relationships: InferredRelationship[];
  warnings?: string[];
  objects_count?: number;
  relationships_count?: number;
}

interface Props {
  data: OntologyPreviewData;
  onConfirm?: () => void;
  onRetry?: () => void;
}

export function OntologyConfirmPanel({ data, onConfirm, onRetry }: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggle = (name: string) =>
    setExpanded((prev) => ({ ...prev, [name]: !prev[name] }));

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-300">建模结果</span>
        {data.template_name && (
          <span className="text-xs text-blue-400">已套用：{data.template_name}</span>
        )}
      </div>

      <div>
        <p className="text-sm text-gray-400 mb-2">
          业务对象 ({data.objects?.length ?? 0})
        </p>
        <div className="space-y-1.5">
          {(data.objects || []).map((obj) => (
            <div key={obj.name} className="border-l-2 border-blue-500 pl-3">
              <button
                onClick={() => toggle(obj.name)}
                className="text-left w-full text-sm text-gray-200 hover:text-white"
              >
                <span className="font-medium">📦 {obj.name}</span>
                {obj.description && (
                  <span className="text-gray-500 ml-2">— {obj.description}</span>
                )}
                <span className="text-gray-500 ml-2 text-xs">
                  ({obj.properties.length} 个字段)
                </span>
              </button>
              {expanded[obj.name] && (
                <div className="mt-1 ml-2 space-y-0.5 text-xs">
                  {obj.properties.map((p) => (
                    <div key={p.name} className="text-gray-400">
                      <span className="text-gray-200">{p.name}</span>
                      <span className="ml-2">{p.data_type}</span>
                      {p.semantic_type && (
                        <span className="ml-2 text-blue-400">
                          ({p.semantic_type})
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {data.relationships && data.relationships.length > 0 && (
        <div>
          <p className="text-sm text-gray-400 mb-2">
            关系 ({data.relationships.length})
          </p>
          <div className="space-y-1 text-xs text-gray-300">
            {data.relationships.map((r, i) => (
              <div key={i}>
                🔗 {r.from_object} → {r.to_object}
                <span className="text-gray-500 ml-2">
                  按 {r.from_field} 关联
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.warnings && data.warnings.length > 0 && (
        <div className="border-l-2 border-yellow-500 pl-3 text-xs text-yellow-400">
          {data.warnings.map((w, i) => (
            <p key={i}>⚠ {w}</p>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={onConfirm}
          className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm text-white transition-colors"
        >
          ✓ 确认建模
        </button>
        <button
          onClick={onRetry}
          className="flex-1 py-2 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm text-gray-200 transition-colors"
        >
          ↻ 重新分析
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Wire into StructuredMessage**

In `frontend/src/components/chat/StructuredMessage.tsx`, modify the `case 'panel':` block:

```tsx
case 'panel':
  if (item.panel_type === 'quality_report') {
    const qdata = item.data as { score: number; issues: any[] } | undefined;
    return <QualityPanel key={i} data={qdata || { score: 0, issues: [] }} />;
  }
  if (item.panel_type === 'ontology_preview') {
    return (
      <OntologyConfirmPanel
        key={i}
        data={item.data as any || { objects: [], relationships: [] }}
        onConfirm={() => onOptionSelect?.('确认建模')}
        onRetry={() => onOptionSelect?.('重新分析建模')}
      />
    );
  }
  return <p key={i} className="text-sm">{item.content}</p>;
```

Add the import at the top:

```tsx
import { OntologyConfirmPanel } from './OntologyConfirmPanel';
```

- [ ] **Step 5: Build frontend**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/.worktrees/phase3b-modeling/frontend
npm run build
```
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/structured_response.py frontend/src/components/chat/OntologyConfirmPanel.tsx frontend/src/components/chat/StructuredMessage.tsx
git commit -m "feat: add OntologyConfirmPanel for ontology_preview structured panels"
```

---

### Task 12: End-to-End Modeling Flow Test

**Files:**
- Create: `backend/tests/test_modeling_flow.py`

- [ ] **Step 1: Write integration test**

```python
# backend/tests/test_modeling_flow.py
"""End-to-end test of the conversational modeling flow."""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from app.services.agent_tools import AgentToolkit
from app.services.uploaded_table_store import UploadedTableStore
from app.services.ontology_draft_store import OntologyDraftStore
from app.schemas.auto_model import InferredObject, InferredProperty


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # ensure templates dir is reachable
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
    # Setup: project + uploaded data
    fake_project = MagicMock(tenant_id=42, owner_id=42, setup_stage="cleaning")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = fake_project

    df = pd.DataFrame({"客户": ["a", "b"], "金额": [100, 200]})
    UploadedTableStore.save(1, 2, "orders", df)

    # Stub LLM
    monkeypatch.setattr(
        "app.services.ontology_inferrer.OntologyInferrer.__init__",
        lambda self: None,
    )
    monkeypatch.setattr(
        "app.services.ontology_inferrer.OntologyInferrer.infer_table",
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

    # Stub OntologyImporter
    imported = {}

    class FakeImporter:
        def __init__(self, _db):
            pass

        def import_dict(self, tenant_id, config):
            imported["tenant_id"] = tenant_id
            imported["object_count"] = len(config["ontology"]["objects"])
            return {"objects_created": len(config["ontology"]["objects"]), "objects_updated": 0, "relationships_created": 0}

    monkeypatch.setattr("app.services.agent_tools.OntologyImporter", FakeImporter)

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

    monkeypatch.setattr("app.services.agent_tools.OntologyStore", FakeStore)
    r = toolkit.execute_tool("edit_ontology", {
        "action": "rename_property",
        "object_name": "订单",
        "property_name": "金额",
        "new_value": "总金额",
    })
    assert r["success"] is True
```

- [ ] **Step 2: Run tests**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/test_modeling_flow.py -v
```
Expected: 1 passed.

- [ ] **Step 3: Run full test suite for regression**

```bash
/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python -m pytest tests/ --tb=line -q 2>&1 | tail -15
```
Expected: known 9 pre-existing failures, no new failures. Total passed should be ≥ 410 + new tests added in this plan (~25).

- [ ] **Step 4: Final frontend build check**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/.worktrees/phase3b-modeling/frontend
npm run build
```
Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_modeling_flow.py
git commit -m "test: end-to-end modeling flow integration test"
```
