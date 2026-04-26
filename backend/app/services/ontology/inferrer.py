import json
import re
from typing import Optional
from app.config import settings

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
from app.services.ontology.schema_scanner import TableSummary
from app.schemas.auto_model import (
    TableClassification, InferredObject, InferredProperty,
    InferredRelationship, SEMANTIC_TYPES,
)


CLASSIFY_PROMPT = """分析以下数据库表，将每张表分类为：business（业务表）、system（系统表）、temporary（临时表）、unknown（未知）。

表列表：
{tables_text}

只输出JSON数组，不要其他文字。格式：
[{{"name": "表名", "category": "business|system|temporary|unknown", "confidence": 0.0-1.0, "description": "一句话描述"}}]"""

INFER_PROMPT = """分析以下数据库表，推断其业务含义。

表名: {table_name}
行数: {row_count}
字段:
{columns_text}

要求：
1. name: 给出中文业务名称
2. source_entity: 保持原始表名 "{table_name}"
3. description: 一句话描述这张表的业务含义
4. business_context: 描述这张表在业务流程中的角色
5. domain: 推断所属行业（retail/manufacturing/trade/service等）
6. properties: 必须是 JSON 数组 (list of objects)，每个元素形如
   {{"name": "字段名", "data_type": "string|number|datetime|...", "semantic_type": "..."}}
   semantic_type 必须从以下列表中选择，找不到合适的设为 null：
   {semantic_types}

只输出JSON对象（顶层是 dict，properties 是 array），不要其他文字。

示例（仅供格式参考，实际内容根据数据推断）：
{{"name": "订单", "source_entity": "{table_name}", "description": "...", "business_context": "...", "domain": "retail", "properties": [{{"name": "order_id", "data_type": "string", "semantic_type": "order_id"}}, {{"name": "amount", "data_type": "number", "semantic_type": "currency_cny"}}]}}"""


class OntologyInferrer:
    def __init__(self):
        self.client = self._create_client()
        self.model = self._get_model()

    def _create_client(self) -> Optional["OpenAI"]:
        if OpenAI is None:
            return None
        if settings.DEEPSEEK_API_KEY:
            return OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)
        if settings.OPENAI_API_KEY:
            return OpenAI(api_key=settings.OPENAI_API_KEY)
        return None

    def _get_model(self) -> str:
        if settings.DEEPSEEK_API_KEY:
            return settings.DEEPSEEK_MODEL
        return "gpt-4o-mini"

    def _call_llm(self, prompt: str) -> str:
        if not self.client:
            raise RuntimeError("No LLM API key configured")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=settings.INFER_TIMEOUT,
        )
        return response.choices[0].message.content or ""

    def _extract_json(self, text: str) -> Optional[dict | list]:
        for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    continue
        return None

    def _validate_semantic_types(self, obj: InferredObject) -> InferredObject:
        for prop in obj.properties:
            if prop.semantic_type and prop.semantic_type not in SEMANTIC_TYPES:
                prop.semantic_type = None
        return obj

    def classify_tables(self, tables: list[TableSummary]) -> list[TableClassification]:
        tables_text = "\n".join(
            f"- {t.name} (字段: {', '.join(c['name'] for c in t.columns)}) 行数: {t.row_count}"
            for t in tables
        )
        prompt = CLASSIFY_PROMPT.format(tables_text=tables_text)
        try:
            raw = self._call_llm(prompt)
            parsed = self._extract_json(raw)
            if not isinstance(parsed, list):
                return [TableClassification(name=t.name) for t in tables]
            return [TableClassification.model_validate(item) for item in parsed]
        except Exception:
            return [TableClassification(name=t.name) for t in tables]

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

    def infer_relationships_by_naming(self, objects: list[InferredObject]) -> list[InferredRelationship]:
        source_entities = {obj.source_entity: obj for obj in objects}
        relationships = []
        for obj in objects:
            for prop in obj.properties:
                if not prop.name.endswith("_id") or prop.name == "id":
                    continue
                ref_name = prop.name[:-3]
                for candidate_entity, candidate_obj in source_entities.items():
                    bare = candidate_entity.removeprefix("t_").removeprefix("tbl_")
                    if ref_name == candidate_entity or ref_name == bare:
                        rel_name = f"{obj.source_entity}_{candidate_entity}"
                        relationships.append(InferredRelationship(
                            name=rel_name,
                            from_object=obj.source_entity,
                            to_object=candidate_entity,
                            from_field=prop.name,
                            to_field="id",
                        ))
                        break
        return relationships


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
