# Agent 内核重写 P0 — Task 5-6

> 续接 `2026-04-27-agent-rewrite-p0.md` Task 4 之后。

---

### Task 5: 内置工具迁移 — modeling + ingestion

**Files:**
- Create: `backend/app/services/agent/tools/builtin/modeling.py`
- Create: `backend/app/services/agent/tools/builtin/ingestion.py`
- Create: `backend/app/services/agent/tools/builtin/asset.py`
- Test: `backend/tests/unit/agent/test_builtin_modeling.py`
- Test: `backend/tests/unit/agent/test_builtin_ingestion.py`

- [ ] **Step 1: 写 modeling 工具的测试**

```python
# backend/tests/unit/agent/test_builtin_modeling.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.agent.tools.registry import ToolContext, ToolResult


@pytest.fixture
def ctx():
    return ToolContext(
        tenant_id=1, project_id=10, session_id=100,
        db=MagicMock(), omaha_service=None,
        ontology_context={}, uploaded_tables={"orders": MagicMock()},
    )


@pytest.mark.asyncio
async def test_scan_tables_no_data():
    from app.services.agent.tools.builtin.modeling import scan_tables
    ctx = ToolContext(
        tenant_id=1, project_id=1, session_id=1,
        db=None, omaha_service=None, ontology_context={}, uploaded_tables={},
    )
    result = await scan_tables(ctx)
    assert result.success is False
    assert "没有" in result.error


@pytest.mark.asyncio
async def test_scan_tables_with_data(ctx):
    import pandas as pd
    from app.services.agent.tools.builtin.modeling import scan_tables
    ctx.uploaded_tables = {"orders": pd.DataFrame({"id": [1, 2], "amount": [100, 200]})}
    result = await scan_tables(ctx)
    assert result.success is True
    assert len(result.data["tables"]) == 1
    assert result.data["tables"][0]["name"] == "orders"
    assert result.data["tables"][0]["row_count"] == 2


@pytest.mark.asyncio
async def test_confirm_ontology_no_draft(ctx):
    from app.services.agent.tools.builtin.modeling import confirm_ontology
    with patch("app.services.agent.tools.builtin.modeling.OntologyDraftStore") as mock_ds:
        mock_ds.load.return_value = None
        result = await confirm_ontology(ctx)
    assert result.success is False
    assert "草稿" in result.error
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
python -m pytest tests/unit/agent/test_builtin_modeling.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 modeling.py**

从 `toolkit.py` 迁移 `_scan_tables`, `_infer_ontology`, `_confirm_ontology`, `_edit_ontology`, `_load_template`。关键变化：
- `self` → `ctx: ToolContext`
- `self._load_tables()` → `ctx.uploaded_tables`
- `self.project_id` → `ctx.project_id`
- `self.db` → `ctx.db`
- 返回 `ToolResult` 而非 `dict`
- 函数变为 `async def`
- 每个函数加 `@register_tool` 装饰器

```python
# backend/app/services/agent/tools/builtin/modeling.py
"""Modeling tools — migrated from AgentToolkit."""
from __future__ import annotations
from typing import Any
from app.services.agent.tools.registry import register_tool, ToolContext, ToolResult


def _summarize_dataframe(name: str, df) -> dict:
    return {
        "name": name,
        "row_count": int(len(df)),
        "columns": [{"name": str(c), "type": str(df[c].dtype)} for c in df.columns],
        "sample_values": {
            str(c): [str(v) for v in df[c].dropna().astype(str).head(20).tolist()]
            for c in df.columns
        },
    }


@register_tool(
    name="scan_tables",
    description="扫描已上传的数据表，返回每张表的列、行数和样本值。在准备建模前调用。",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def scan_tables(ctx: ToolContext) -> ToolResult:
    tables = ctx.uploaded_tables
    if not tables:
        return ToolResult(success=False, error="没有已上传的数据，请先上传文件")
    summaries = [_summarize_dataframe(name, df) for name, df in tables.items()]
    return ToolResult(success=True, data={"tables": summaries})


@register_tool(
    name="load_template",
    description="加载行业模板，返回该行业典型的业务对象定义。",
    parameters={
        "type": "object",
        "properties": {"industry": {"type": "string", "description": "行业代码：retail / manufacturing / trade / service"}},
        "required": ["industry"],
    },
)
async def load_template(ctx: ToolContext, industry: str) -> ToolResult:
    from app.services.ontology.template_loader import TemplateLoader
    template = TemplateLoader.load(industry)
    if not template:
        return ToolResult(success=False, error=f"未知行业模板: {industry}")
    return ToolResult(success=True, data={
        "industry": template.get("industry", industry),
        "display_name": template.get("display_name", industry),
        "domain": template.get("domain", industry),
        "objects": template.get("objects", []),
        "relationships": template.get("relationships", []),
    })


@register_tool(
    name="infer_ontology",
    description="基于已上传数据 + 可选行业模板，调 LLM 推断本体。结果存为草稿。",
    parameters={
        "type": "object",
        "properties": {"industry": {"type": "string", "description": "行业代码（可选）"}},
        "required": [],
    },
)
async def infer_ontology(ctx: ToolContext, industry: str | None = None) -> ToolResult:
    from app.services.ontology.inferrer import OntologyInferrer, compact_template, merge_template_semantic_types
    from app.services.ontology.draft_store import OntologyDraftStore
    from app.services.ontology.template_loader import TemplateLoader
    from app.services.ontology.schema_scanner import TableSummary

    if ctx.project_id is None or ctx.session_id is None:
        return ToolResult(success=False, error="project_id/session_id missing")
    tables = ctx.uploaded_tables
    if not tables:
        return ToolResult(success=False, error="没有已上传的数据，请先上传文件")

    template = None
    template_hint = None
    if industry:
        template = TemplateLoader.load(industry)
        if template:
            template_hint = compact_template(template)

    inferrer = OntologyInferrer()
    inferred_objects = []
    warnings: list[str] = []
    for name, df in tables.items():
        summary_dict = _summarize_dataframe(name, df)
        summary = TableSummary(
            name=summary_dict["name"], row_count=summary_dict["row_count"],
            columns=[{**c, "nullable": True} for c in summary_dict["columns"]],
            sample_values=summary_dict["sample_values"],
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
        project_id=ctx.project_id, session_id=ctx.session_id,
        objects=[obj.model_dump() for obj in inferred_objects],
        relationships=[rel.model_dump() for rel in relationships],
        warnings=warnings,
    )

    if not inferred_objects:
        return ToolResult(success=False, error="LLM 未能推断出业务对象。" + ("; ".join(warnings) if warnings else ""))

    return ToolResult(success=True, data={
        "objects_count": len(inferred_objects),
        "relationships_count": len(relationships),
        "warnings": warnings,
        "objects": [obj.model_dump() for obj in inferred_objects],
        "relationships": [rel.model_dump() for rel in relationships],
        "template_name": template.get("display_name") if template else None,
    })


# Import OntologyDraftStore at module level for confirm/edit
from app.services.ontology.draft_store import OntologyDraftStore


@register_tool(
    name="confirm_ontology",
    description="用户确认建模草稿后调用。把草稿持久化到本体库，setup_stage 推到 ready。",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def confirm_ontology(ctx: ToolContext) -> ToolResult:
    from app.services.ontology.importer import OntologyImporter
    from app.models.project.project import Project

    if ctx.project_id is None or ctx.session_id is None or ctx.db is None:
        return ToolResult(success=False, error="project_id/session_id/db missing")

    draft = OntologyDraftStore.load(ctx.project_id, ctx.session_id)
    if not draft or not draft.get("objects"):
        return ToolResult(success=False, error="没有可确认的草稿，请先调用 infer_ontology")

    project = ctx.db.query(Project).filter(Project.id == ctx.project_id).first()
    if not project:
        return ToolResult(success=False, error=f"project {ctx.project_id} not found")

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
                        {"name": p["name"], "type": p.get("data_type", "string"),
                         "semantic_type": p.get("semantic_type"), "description": p.get("description")}
                        for p in obj.get("properties", [])
                    ],
                }
                for obj in draft["objects"]
            ],
        },
    }

    importer = OntologyImporter(ctx.db)
    result = importer.import_dict(tenant_id, config)
    project.setup_stage = "ready"
    ctx.db.commit()
    OntologyDraftStore.clear(ctx.project_id, ctx.session_id)

    return ToolResult(success=True, data={
        "objects_created": result.get("objects_created", 0),
        "objects_updated": result.get("objects_updated", 0),
        "relationships_created": result.get("relationships_created", 0),
    })


@register_tool(
    name="edit_ontology",
    description="修改已确认的本体（重命名、改语义类型、增删字段或关系）。",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "rename_object | rename_property | change_semantic_type | update_description | add_property | remove_property | add_relationship | remove_relationship"},
            "object_name": {"type": "string"},
            "property_name": {"type": "string"},
            "new_value": {"type": "string"},
            "data_type": {"type": "string"},
            "semantic_type": {"type": "string"},
            "to_object": {"type": "string"},
            "from_field": {"type": "string"},
            "to_field": {"type": "string"},
        },
        "required": ["action", "object_name"],
    },
)
async def edit_ontology(ctx: ToolContext, action: str, object_name: str, **kwargs: Any) -> ToolResult:
    from app.models.project.project import Project
    from app.services.ontology.store import OntologyStore
    from sqlalchemy.exc import SQLAlchemyError

    if ctx.project_id is None or ctx.db is None:
        return ToolResult(success=False, error="project_id/db missing")

    project = ctx.db.query(Project).filter(Project.id == ctx.project_id).first()
    if not project:
        return ToolResult(success=False, error=f"project {ctx.project_id} not found")
    if project.setup_stage != "ready":
        return ToolResult(success=False, error="edit_ontology 仅在已确认本体后可用 (setup_stage=ready)")

    required_by_action = {
        "rename_object": ("new_value",),
        "rename_property": ("property_name", "new_value"),
        "change_semantic_type": ("property_name", "new_value"),
        "update_description": ("new_value",),
        "add_property": ("property_name",),
        "remove_property": ("property_name",),
        "add_relationship": ("to_object", "from_field", "to_field"),
        "remove_relationship": (),
    }
    if action not in required_by_action:
        return ToolResult(success=False, error=f"未知 action: {action}")
    missing = [k for k in required_by_action[action] if not kwargs.get(k)]
    if missing:
        return ToolResult(success=False, error=f"缺少参数: {', '.join(missing)}")

    tenant_id = project.tenant_id or project.owner_id
    store = OntologyStore(ctx.db)
    obj = store.get_object(tenant_id, object_name)
    if obj is None:
        return ToolResult(success=False, error=f"未找到对象: {object_name}")

    try:
        ok = _dispatch_edit(store, tenant_id, obj, action, object_name, kwargs)
        if not ok:
            return ToolResult(success=False, error=f"操作失败: {action}")
        ctx.db.commit()
        return ToolResult(success=True, data={"action": action, "object_name": object_name})
    except SQLAlchemyError as e:
        ctx.db.rollback()
        return ToolResult(success=False, error=f"数据库错误: {e}")


def _dispatch_edit(store, tenant_id, obj, action, object_name, kwargs) -> bool:
    if action == "rename_object":
        return store.rename_object(tenant_id, object_name, kwargs["new_value"])
    elif action == "rename_property":
        return store.rename_property(obj.id, kwargs["property_name"], kwargs["new_value"])
    elif action == "change_semantic_type":
        return store.update_property_semantic_type(obj.id, kwargs["property_name"], kwargs["new_value"])
    elif action == "update_description":
        if kwargs.get("property_name"):
            return store.update_property_description(obj.id, kwargs["property_name"], kwargs["new_value"])
        return store.update_object_description(tenant_id, object_name, kwargs["new_value"])
    elif action == "add_property":
        store.add_property(object_id=obj.id, name=kwargs["property_name"],
                           data_type=kwargs.get("data_type", "string"), semantic_type=kwargs.get("semantic_type"))
        return True
    elif action == "remove_property":
        return store.remove_property(obj.id, kwargs["property_name"])
    elif action == "add_relationship":
        to_obj = store.get_object(tenant_id, kwargs["to_object"])
        if not to_obj:
            return False
        store.add_relationship(tenant_id=tenant_id, name=f"{object_name}_{kwargs['to_object']}",
                               from_object_id=obj.id, to_object_id=to_obj.id,
                               relationship_type=kwargs.get("relationship_type", "belongs_to"),
                               from_field=kwargs["from_field"], to_field=kwargs["to_field"])
        return True
    else:
        return store.remove_relationship(tenant_id, kwargs.get("new_value") or object_name)
```

- [ ] **Step 4: 运行 modeling 测试确认通过**

```bash
python -m pytest tests/unit/agent/test_builtin_modeling.py -v
```

Expected: 3 passed

- [ ] **Step 5: 写 ingestion 工具的测试**

```python
# backend/tests/unit/agent/test_builtin_ingestion.py
import pytest
from unittest.mock import MagicMock, patch
from app.services.agent.tools.registry import ToolContext, ToolResult


@pytest.fixture
def ctx():
    return ToolContext(
        tenant_id=1, project_id=10, session_id=100,
        db=None, omaha_service=None, ontology_context={}, uploaded_tables={},
    )


@pytest.mark.asyncio
async def test_assess_quality_no_data(ctx):
    from app.services.agent.tools.builtin.ingestion import assess_quality
    result = await assess_quality(ctx)
    assert result.success is False
    assert "没有" in result.error


@pytest.mark.asyncio
async def test_assess_quality_with_data(ctx):
    import pandas as pd
    from app.services.agent.tools.builtin.ingestion import assess_quality
    ctx.uploaded_tables = {"t1": pd.DataFrame({"a": [1, 2, 3]})}
    with patch("app.services.agent.tools.builtin.ingestion.DataCleaner") as mock_dc:
        mock_report = MagicMock()
        mock_report.to_dict.return_value = {"score": 85, "issues": []}
        mock_dc.assess.return_value = mock_report
        result = await assess_quality(ctx)
    assert result.success is True
    assert result.data["score"] == 85


@pytest.mark.asyncio
async def test_clean_data_no_data(ctx):
    from app.services.agent.tools.builtin.ingestion import clean_data
    result = await clean_data(ctx, rules=["strip_whitespace"])
    assert result.success is False
```

- [ ] **Step 6: 实现 ingestion.py**

```python
# backend/app/services/agent/tools/builtin/ingestion.py
"""Ingestion tools — migrated from AgentToolkit."""
from __future__ import annotations
from app.services.agent.tools.registry import register_tool, ToolContext, ToolResult


@register_tool(
    name="upload_file",
    description="解析 Excel/CSV 文件并存入平台。",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "上传文件的服务器路径"},
            "table_name": {"type": "string", "description": "存储的表名"},
        },
        "required": ["file_path", "table_name"],
    },
)
async def upload_file(ctx: ToolContext, file_path: str, table_name: str) -> ToolResult:
    import pandas as pd
    try:
        if file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
        ctx.uploaded_tables[table_name] = df
        return ToolResult(success=True, data={
            "table_name": table_name, "row_count": len(df),
            "column_count": len(df.columns),
            "columns": [{"name": c, "type": str(df[c].dtype)} for c in df.columns],
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@register_tool(
    name="assess_quality",
    description="评估已上传数据的质量，返回质量评分和问题清单。",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def assess_quality(ctx: ToolContext) -> ToolResult:
    from app.services.data.cleaner import DataCleaner
    if not ctx.uploaded_tables:
        return ToolResult(success=False, error="没有已上传的数据，请先上传文件")
    report = DataCleaner.assess(ctx.uploaded_tables)
    return ToolResult(success=True, data=report.to_dict())


@register_tool(
    name="clean_data",
    description="对已上传的数据执行清洗操作。rules: duplicate_rows / strip_whitespace / standardize_dates",
    parameters={
        "type": "object",
        "properties": {"rules": {"type": "array", "items": {"type": "string"}, "description": "清洗规则列表"}},
        "required": ["rules"],
    },
)
async def clean_data(ctx: ToolContext, rules: list[str]) -> ToolResult:
    from app.services.data.cleaner import DataCleaner
    if not ctx.uploaded_tables:
        return ToolResult(success=False, error="没有已上传的数据")
    cleaned = DataCleaner.clean(ctx.uploaded_tables, auto_rules=rules)
    summary = {f"{name}_cleaned": len(df) for name, df in cleaned.items()}
    ctx.uploaded_tables.update(cleaned)
    return ToolResult(success=True, data=summary)
```

- [ ] **Step 7: 实现 asset.py（stub）**

```python
# backend/app/services/agent/tools/builtin/asset.py
"""Asset tools — save_asset, list_assets, get_lineage."""
from __future__ import annotations
from app.services.agent.tools.registry import register_tool, ToolContext, ToolResult


@register_tool(
    name="save_asset",
    description="保存命名查询为资产。",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "资产名称"},
            "query_config": {"type": "object", "description": "查询配置"},
        },
        "required": ["name", "query_config"],
    },
)
async def save_asset(ctx: ToolContext, name: str, query_config: dict) -> ToolResult:
    return ToolResult(success=True, data={"asset_name": name, "status": "saved"})


@register_tool(
    name="list_assets",
    description="列出已保存的资产。",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def list_assets(ctx: ToolContext) -> ToolResult:
    return ToolResult(success=True, data={"assets": []})


@register_tool(
    name="get_lineage",
    description="获取资产的数据血缘。",
    parameters={
        "type": "object",
        "properties": {"asset_name": {"type": "string"}},
        "required": ["asset_name"],
    },
)
async def get_lineage(ctx: ToolContext, asset_name: str) -> ToolResult:
    return ToolResult(success=True, data={"lineage": []})
```

- [ ] **Step 8: 运行全部新测试**

```bash
python -m pytest tests/unit/agent/test_builtin_modeling.py tests/unit/agent/test_builtin_ingestion.py -v
```

Expected: 6 passed

- [ ] **Step 9: 运行全量测试确认无回归**

```bash
python -m pytest tests/ -x -q 2>&1 | tail -5
```

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/agent/tools/builtin/
git add backend/tests/unit/agent/test_builtin_modeling.py backend/tests/unit/agent/test_builtin_ingestion.py
git commit -m "feat(agent): migrate modeling + ingestion + asset tools to ToolRegistry"
```

---

### Task 6: Skill 系统 — YAML 定义 + Loader + Resolver

**Files:**
- Create: `backend/app/services/agent/skills/definitions/onboarding.yaml`
- Create: `backend/app/services/agent/skills/definitions/data_ingestion.yaml`
- Create: `backend/app/services/agent/skills/definitions/data_modeling.yaml`
- Create: `backend/app/services/agent/skills/definitions/data_query.yaml`
- Create: `backend/app/services/agent/skills/loader.py`
- Create: `backend/app/services/agent/skills/resolver.py`
- Test: `backend/tests/unit/agent/test_skills.py`

- [ ] **Step 1: 创建 4 个 Skill YAML 定义**

```yaml
# backend/app/services/agent/skills/definitions/onboarding.yaml
name: onboarding
description: 新用户引导
trigger_keywords: []
system_prompt: |
  ## 当前状态：新用户引导
  用户刚创建项目，还没有接入数据。你的任务是引导用户完成数据接入。
  1. 先问用户是什么行业的
  2. 再问用什么方式管理数据（Excel/数据库/SaaS软件）
  3. 引导用户上传文件或填写连接信息
  用业务语言，不要用技术术语。
allowed_tools: []
```

```yaml
# backend/app/services/agent/skills/definitions/data_ingestion.yaml
name: data_ingestion
description: 数据接入与清洗
trigger_keywords: ["上传", "导入", "接入", "文件", "Excel", "CSV", "清洗", "质量"]
system_prompt: |
  ## 当前状态：数据接入中
  用户正在接入数据源。如果上传了文件，自动调用 assess_quality 评估数据质量。
  展示质量问题，引导用户确认清洗方案。
allowed_tools:
  - upload_file
  - assess_quality
  - clean_data
```

```yaml
# backend/app/services/agent/skills/definitions/data_modeling.yaml
name: data_modeling
description: 语义建模
trigger_keywords: ["建模", "整理", "梳理", "识别", "对象", "模板", "修改对象", "编辑本体"]
system_prompt: |
  ## 当前状态：语义建模中
  数据已清洗，正在构建本体。引导用户确认业务对象和字段含义。
  建模请求必须走工具链：load_template → scan_tables → infer_ontology。
  infer_ontology 成功后必须返回 ontology_preview 结构化块。
  用户说"确认"时立即调用 confirm_ontology。
allowed_tools:
  - load_template
  - scan_tables
  - infer_ontology
  - confirm_ontology
  - edit_ontology
```

```yaml
# backend/app/services/agent/skills/definitions/data_query.yaml
name: data_query
description: 数据查询与分析
trigger_keywords: ["查询", "多少", "分析", "趋势", "对比", "统计", "报表"]
system_prompt: |
  你是数据分析专家。用户已完成数据建模，现在需要查询和分析业务数据。
  - 任何涉及具体数据的问题，必须先调用工具查询
  - 查询一次后立即基于结果回答，不要反复查询
  - 如果数据触发健康规则阈值，主动提醒
allowed_tools:
  - query_data
  - list_objects
  - get_schema
  - get_relationships
  - generate_chart
  - auto_chart
  - save_asset
  - list_assets
  - get_lineage
  - screen_stocks
```

- [ ] **Step 2: 写 Skill 系统的测试**

```python
# backend/tests/unit/agent/test_skills.py
import pytest
from pathlib import Path


def test_skill_loader_loads_all():
    from app.services.agent.skills.loader import SkillLoader, Skill
    skills_dir = Path(__file__).parent.parent.parent.parent / "app/services/agent/skills/definitions"
    loader = SkillLoader(skills_dir)
    skills = loader.load_all()
    names = [s.name for s in skills]
    assert "onboarding" in names
    assert "data_ingestion" in names
    assert "data_modeling" in names
    assert "data_query" in names


def test_skill_loader_load_by_name():
    from app.services.agent.skills.loader import SkillLoader
    skills_dir = Path(__file__).parent.parent.parent.parent / "app/services/agent/skills/definitions"
    loader = SkillLoader(skills_dir)
    skill = loader.load("data_query")
    assert skill is not None
    assert skill.name == "data_query"
    assert "query_data" in skill.allowed_tools
    assert len(skill.system_prompt) > 0


def test_skill_loader_load_missing():
    from app.services.agent.skills.loader import SkillLoader
    skills_dir = Path(__file__).parent.parent.parent.parent / "app/services/agent/skills/definitions"
    loader = SkillLoader(skills_dir)
    skill = loader.load("nonexistent")
    assert skill is None


def test_skill_resolver_by_stage():
    from app.services.agent.skills.resolver import SkillResolver
    from app.services.agent.skills.loader import SkillLoader
    skills_dir = Path(__file__).parent.parent.parent.parent / "app/services/agent/skills/definitions"
    resolver = SkillResolver(SkillLoader(skills_dir))

    skill = resolver.resolve(setup_stage="idle", user_message="你好")
    assert skill.name == "onboarding"

    skill = resolver.resolve(setup_stage="connecting", user_message="")
    assert skill.name == "data_ingestion"

    skill = resolver.resolve(setup_stage="modeling", user_message="")
    assert skill.name == "data_modeling"

    skill = resolver.resolve(setup_stage="ready", user_message="上个月销售额多少")
    assert skill.name == "data_query"


def test_skill_resolver_keyword_override():
    from app.services.agent.skills.resolver import SkillResolver
    from app.services.agent.skills.loader import SkillLoader
    skills_dir = Path(__file__).parent.parent.parent.parent / "app/services/agent/skills/definitions"
    resolver = SkillResolver(SkillLoader(skills_dir))

    # In ready stage, keyword "修改对象" should switch to data_modeling
    skill = resolver.resolve(setup_stage="ready", user_message="帮我修改对象的字段")
    assert skill.name == "data_modeling"
```

- [ ] **Step 3: 运行测试确认失败**

```bash
python -m pytest tests/unit/agent/test_skills.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: 实现 loader.py**

```python
# backend/app/services/agent/skills/loader.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class Skill:
    name: str
    description: str
    system_prompt: str
    allowed_tools: list[str] = field(default_factory=list)
    trigger_keywords: list[str] = field(default_factory=list)


class SkillLoader:
    def __init__(self, definitions_dir: Path | str | None = None):
        if definitions_dir is None:
            definitions_dir = Path(__file__).parent / "definitions"
        self._dir = Path(definitions_dir)

    def load_all(self) -> list[Skill]:
        skills = []
        for f in sorted(self._dir.glob("*.yaml")):
            skill = self._parse(f)
            if skill:
                skills.append(skill)
        return skills

    def load(self, name: str) -> Skill | None:
        path = self._dir / f"{name}.yaml"
        if not path.exists():
            return None
        return self._parse(path)

    @staticmethod
    def _parse(path: Path) -> Skill | None:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return Skill(
                name=data["name"],
                description=data.get("description", ""),
                system_prompt=data.get("system_prompt", ""),
                allowed_tools=data.get("allowed_tools", []),
                trigger_keywords=data.get("trigger_keywords", []),
            )
        except Exception:
            return None
```

- [ ] **Step 5: 实现 resolver.py**

```python
# backend/app/services/agent/skills/resolver.py
from __future__ import annotations
from app.services.agent.skills.loader import Skill, SkillLoader


STAGE_TO_SKILL: dict[str, str] = {
    "idle": "onboarding",
    "connecting": "data_ingestion",
    "cleaning": "data_ingestion",
    "modeling": "data_modeling",
    "ready": "data_query",
}


class SkillResolver:
    def __init__(self, loader: SkillLoader):
        self._loader = loader
        self._skills = {s.name: s for s in loader.load_all()}

    def resolve(self, setup_stage: str | None, user_message: str) -> Skill:
        # 1. Stage-based primary match
        stage_skill_name = STAGE_TO_SKILL.get(setup_stage or "ready", "data_query")

        # 2. In ready stage, check keyword override
        if stage_skill_name == "data_query" and user_message:
            for skill in self._skills.values():
                if skill.name == "data_query":
                    continue
                if any(kw in user_message for kw in skill.trigger_keywords):
                    return skill

        return self._skills.get(stage_skill_name, self._get_fallback())

    def _get_fallback(self) -> Skill:
        return self._skills.get("data_query") or Skill(
            name="fallback", description="", system_prompt="", allowed_tools=[], trigger_keywords=[],
        )
```

- [ ] **Step 6: 运行测试确认通过**

```bash
python -m pytest tests/unit/agent/test_skills.py -v
```

Expected: 5 passed

- [ ] **Step 7: 运行全量测试确认无回归**

```bash
python -m pytest tests/ -x -q 2>&1 | tail -5
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/agent/skills/
git add backend/tests/unit/agent/test_skills.py
git commit -m "feat(agent): add Skill system with YAML definitions, SkillLoader, and SkillResolver"
```

