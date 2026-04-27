"""Builtin modeling tools — scan_tables, load_template, infer_ontology, confirm_ontology, edit_ontology."""
from __future__ import annotations

from app.services.agent.tools.registry import ToolContext, ToolResult, register_tool


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# scan_tables
# ---------------------------------------------------------------------------

@register_tool(
    "scan_tables",
    "扫描已上传的数据表，返回每张表的列、行数和样本值。在准备建模前调用。",
    {"type": "object", "properties": {}, "required": []},
)
def scan_tables(params: dict, ctx: ToolContext) -> ToolResult:
    tables = ctx.uploaded_tables
    if not tables:
        return ToolResult(success=False, error="没有已上传的数据，请先上传文件")
    summaries = [_summarize_dataframe(name, df) for name, df in tables.items()]
    return ToolResult(success=True, data={"tables": summaries})


# ---------------------------------------------------------------------------
# load_template
# ---------------------------------------------------------------------------

@register_tool(
    "load_template",
    "加载行业模板，返回该行业典型的业务对象定义。在用户告知行业后调用，结果可作为 infer_ontology 的先验。",
    {
        "type": "object",
        "properties": {
            "industry": {
                "type": "string",
                "description": "行业代码：retail / manufacturing / trade / service",
            }
        },
        "required": ["industry"],
    },
)
def load_template(params: dict, ctx: ToolContext) -> ToolResult:
    from app.services.ontology.template_loader import TemplateLoader  # lazy

    industry = params.get("industry")
    if not industry:
        return ToolResult(success=False, error="industry 参数必填")
    template = TemplateLoader.load(industry)
    if not template:
        return ToolResult(success=False, error=f"未知行业模板: {industry}")
    return ToolResult(
        success=True,
        data={
            "industry": template.get("industry", industry),
            "display_name": template.get("display_name", industry),
            "domain": template.get("domain", industry),
            "objects": template.get("objects", []),
            "relationships": template.get("relationships", []),
        },
    )


# ---------------------------------------------------------------------------
# infer_ontology
# ---------------------------------------------------------------------------

@register_tool(
    "infer_ontology",
    "基于已上传数据 + 可选行业模板，调 LLM 推断本体（业务对象、字段语义、关系）。结果存为草稿，用户确认后才生效。",
    {
        "type": "object",
        "properties": {
            "industry": {
                "type": "string",
                "description": "行业代码（可选）。如有值，会先加载对应模板作为 LLM 提示",
            }
        },
        "required": [],
    },
)
def infer_ontology(params: dict, ctx: ToolContext) -> ToolResult:
    from app.services.ontology.inferrer import (  # lazy
        OntologyInferrer,
        compact_template,
        merge_template_semantic_types,
    )
    from app.services.ontology.draft_store import OntologyDraftStore  # lazy
    from app.services.ontology.template_loader import TemplateLoader  # lazy
    from app.services.ontology.schema_scanner import TableSummary  # lazy

    if ctx.project_id is None or ctx.session_id is None:
        return ToolResult(success=False, error="project_id/session_id missing on context")

    tables = ctx.uploaded_tables
    if not tables:
        return ToolResult(success=False, error="没有已上传的数据，请先上传文件")

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
        summary_dict = _summarize_dataframe(name, df)
        summary = TableSummary(
            name=summary_dict["name"],
            row_count=summary_dict["row_count"],
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
        project_id=ctx.project_id,
        session_id=ctx.session_id,
        objects=[obj.model_dump() for obj in inferred_objects],
        relationships=[rel.model_dump() for rel in relationships],
        warnings=warnings,
    )

    if not inferred_objects:
        return ToolResult(
            success=False,
            error="LLM 未能从已上传数据推断出业务对象。" + ("; ".join(warnings) if warnings else ""),
            data={"warnings": warnings},
        )

    return ToolResult(
        success=True,
        data={
            "objects_count": len(inferred_objects),
            "relationships_count": len(relationships),
            "warnings": warnings,
            "objects": [obj.model_dump() for obj in inferred_objects],
            "relationships": [rel.model_dump() for rel in relationships],
            "template_name": template.get("display_name") if template else None,
        },
    )


# ---------------------------------------------------------------------------
# confirm_ontology
# ---------------------------------------------------------------------------

@register_tool(
    "confirm_ontology",
    "用户确认建模草稿后调用。把草稿持久化到本体库，setup_stage 推到 ready。如无草稿则报错。",
    {"type": "object", "properties": {}, "required": []},
)
def confirm_ontology(params: dict, ctx: ToolContext) -> ToolResult:
    from app.services.ontology.draft_store import OntologyDraftStore  # lazy
    from app.services.ontology.importer import OntologyImporter  # lazy
    from app.models.project.project import Project  # lazy

    if ctx.project_id is None or ctx.session_id is None:
        return ToolResult(success=False, error="project_id/session_id missing on context")
    if ctx.db is None:
        return ToolResult(success=False, error="db session missing on context")

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

    importer = OntologyImporter(ctx.db)
    result = importer.import_dict(tenant_id, config)

    project.setup_stage = "ready"
    ctx.db.commit()

    OntologyDraftStore.clear(ctx.project_id, ctx.session_id)

    return ToolResult(
        success=True,
        data={
            "objects_created": result.get("objects_created", 0),
            "objects_updated": result.get("objects_updated", 0),
            "relationships_created": result.get("relationships_created", 0),
        },
    )


# ---------------------------------------------------------------------------
# edit_ontology
# ---------------------------------------------------------------------------

@register_tool(
    "edit_ontology",
    "修改已确认的本体（重命名对象/字段、改语义类型、增删字段或关系）。setup_stage 必须为 ready 才能调用。",
    {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "rename_object | rename_property | change_semantic_type | update_description | add_property | remove_property | add_relationship | remove_relationship",
            },
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
def edit_ontology(params: dict, ctx: ToolContext) -> ToolResult:
    from app.models.project.project import Project  # lazy
    from app.services.ontology.store import OntologyStore  # lazy
    from sqlalchemy.exc import SQLAlchemyError  # lazy

    if ctx.project_id is None or ctx.db is None:
        return ToolResult(success=False, error="project_id/db missing on context")

    project = ctx.db.query(Project).filter(Project.id == ctx.project_id).first()
    if not project:
        return ToolResult(success=False, error=f"project {ctx.project_id} not found")
    if project.setup_stage != "ready":
        return ToolResult(success=False, error="edit_ontology 仅在已确认本体后可用 (setup_stage=ready)")

    action = params.get("action")
    object_name = params.get("object_name")
    if not action or not object_name:
        return ToolResult(success=False, error="action 和 object_name 必填")

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
    missing = [k for k in required_by_action[action] if not params.get(k)]
    if missing:
        return ToolResult(success=False, error=f"缺少参数: {', '.join(missing)}")

    tenant_id = project.tenant_id or project.owner_id
    store = OntologyStore(ctx.db)

    obj = store.get_object(tenant_id, object_name)
    if obj is None:
        return ToolResult(success=False, error=f"未找到对象: {object_name}")

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
                return ToolResult(success=False, error=f"未找到目标对象: {params['to_object']}")
            store.add_relationship(
                tenant_id=tenant_id,
                name=f"{object_name}_{params['to_object']}",
                from_object_id=obj.id,
                to_object_id=to_obj.id,
                relationship_type=params.get("relationship_type", "belongs_to"),
                from_field=params["from_field"],
                to_field=params["to_field"],
            )
            ok = True
        else:  # remove_relationship
            ok = store.remove_relationship(tenant_id, params.get("new_value") or object_name)

        if not ok:
            return ToolResult(success=False, error=f"操作失败: {action}")

        ctx.db.commit()
        return ToolResult(success=True, data={"action": action, "object_name": object_name})

    except SQLAlchemyError as e:
        ctx.db.rollback()
        return ToolResult(success=False, error=f"数据库错误: {e}")
