# Per-ObjectType Query Tools + ObjectSet API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the generic `query_data(filters)` query path with per-object, flat-parameter query tools backed by a minimal immutable ObjectSet layer, while preserving compatibility with the current agent and ontology flow.

**Architecture:** Keep OmahaService as the execution backend. Add slugs to ontology objects/properties, build a per-session derived tool view from the latest ontology on every turn, and let ExecutorAgent consume that view with wildcard whitelist matching and `tool_choice="auto"`.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy ORM, Alembic, pytest, existing ChatServiceV2 / ExecutorAgent / ToolRegistry abstractions

---

## File Structure

**Create:**
- `backend/app/services/ontology/slug.py` — slug generation + uniqueness helpers
- `backend/app/services/agent/objectset/__init__.py` — `Filter`, `Sort`, `ObjectSet`
- `backend/app/services/agent/objectset/compiler.py` — ObjectSet → OmahaService adapter
- `backend/app/services/agent/tools/factory.py` — derive `search_<slug>` / `count_<slug>` ToolSpecs + handlers
- `backend/app/services/agent/tools/view.py` — `ToolRegistryView` combining builtin + derived tools
- `backend/alembic/versions/<new_revision>_add_slug_to_ontology.py` — add slug columns + constraints
- `backend/tests/unit/ontology/test_slug.py` — slug generation + uniqueness tests
- `backend/tests/unit/agent/test_objectset.py` — ObjectSet immutability + compiler tests
- `backend/tests/unit/agent/test_factory.py` — derived tool schema/handler tests
- `backend/tests/unit/agent/test_view.py` — wildcard whitelist + builtin/derived dispatch tests

**Modify:**
- `backend/app/models/ontology/ontology.py` — add `slug` columns + unique constraints
- `backend/app/services/ontology/store.py` — persist/read slug fields; rename helpers update slugs too
- `backend/app/services/ontology/importer.py` — generate and persist object/property slugs during import
- `backend/app/services/agent/chat_service.py` — build per-turn derived tool view from latest ontology
- `backend/app/services/agent/orchestrator/executor.py` — accept registry-like view, make first turn `auto`
- `backend/app/services/agent/skills/definitions/data_query.yaml` — add `search_*` / `count_*` wildcard tools
- `backend/app/services/agent/tools/builtin/query.py` — keep fallback `query_data` unchanged but out of prompt path
- `backend/tests/e2e/test_chat_scenarios_e2e.py` — add/adjust scenarios for `search_<slug>` expectations
- `backend/tests/e2e/test_multiturn_context_e2e.py` — add rename-then-query / modeling-then-query coverage if not already present

---

### Task 1: Add ontology slugs and persistence

**Files:**
- Create: `backend/app/services/ontology/slug.py`
- Create: `backend/alembic/versions/<new_revision>_add_slug_to_ontology.py`
- Modify: `backend/app/models/ontology/ontology.py:14-57`
- Modify: `backend/app/services/ontology/store.py:22-62,97-123,168-220`
- Modify: `backend/app/services/ontology/importer.py:19-75`
- Test: `backend/tests/unit/ontology/test_slug.py`

- [ ] **Step 1: Write the failing slug tests**

```python
# backend/tests/unit/ontology/test_slug.py
from app.services.ontology.slug import ensure_unique_slug, slugify_name


def test_slugify_ascii_name():
    assert slugify_name("Product") == "product"


def test_slugify_non_ascii_name():
    slug = slugify_name("商品")
    assert slug
    assert slug.isascii()


def test_ensure_unique_slug_appends_suffix():
    existing = {"product", "product_2"}
    assert ensure_unique_slug("product", existing) == "product_3"
```

- [ ] **Step 2: Run the slug test to verify it fails**

Run: `cd backend && source venv311/bin/activate && pytest tests/unit/ontology/test_slug.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ontology.slug'`

- [ ] **Step 3: Add slug helpers**

```python
# backend/app/services/ontology/slug.py
from __future__ import annotations

import hashlib
import re
import unicodedata


def slugify_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text).strip("_")
    if slug:
        return slug[:64]
    digest = hashlib.sha1((value or "").encode("utf-8")).hexdigest()[:8]
    return f"obj_{digest}"


def ensure_unique_slug(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    index = 2
    while True:
        candidate = f"{base}_{index}"
        if candidate not in existing:
            return candidate
        index += 1
```

- [ ] **Step 4: Add slug columns and DB constraints**

```python
# backend/app/models/ontology/ontology.py (only changed fields shown)
class OntologyObject(Base):
    __tablename__ = "ontology_objects"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    slug = Column(String(64), nullable=False)
    source_entity = Column(String, nullable=False)
    # ...
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_object_name"),
        UniqueConstraint("tenant_id", "slug", name="uq_tenant_object_slug"),
    )


class ObjectProperty(Base):
    __tablename__ = "object_properties"
    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    slug = Column(String(64), nullable=False)
    data_type = Column(String, nullable=False)
    # ...
    __table_args__ = (
        UniqueConstraint("object_id", "name", name="uq_object_property_name"),
        UniqueConstraint("object_id", "slug", name="uq_object_property_slug"),
    )
```

- [ ] **Step 5: Add the migration**

```python
# backend/alembic/versions/<new_revision>_add_slug_to_ontology.py
from alembic import op
import sqlalchemy as sa


revision = "<new_revision>"
down_revision = "2cf16b1a0c59"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ontology_objects", sa.Column("slug", sa.String(length=64), nullable=True))
    op.add_column("object_properties", sa.Column("slug", sa.String(length=64), nullable=True))
    op.execute("UPDATE ontology_objects SET slug = lower(name)")
    op.execute("UPDATE object_properties SET slug = lower(name)")
    op.alter_column("ontology_objects", "slug", nullable=False)
    op.alter_column("object_properties", "slug", nullable=False)
    op.create_unique_constraint("uq_tenant_object_slug", "ontology_objects", ["tenant_id", "slug"])
    op.create_unique_constraint("uq_object_property_slug", "object_properties", ["object_id", "slug"])


def downgrade() -> None:
    op.drop_constraint("uq_object_property_slug", "object_properties", type_="unique")
    op.drop_constraint("uq_tenant_object_slug", "ontology_objects", type_="unique")
    op.drop_column("object_properties", "slug")
    op.drop_column("ontology_objects", "slug")
```

- [ ] **Step 6: Persist slugs in store/importer**

```python
# backend/app/services/ontology/store.py (changed signatures shown)
def create_object(self, tenant_id: int, name: str, slug: str, source_entity: str,
                  datasource_id: str, datasource_type: str,
                  description: str = None, business_context: str = None,
                  domain: str = None, default_filters: list = None) -> OntologyObject:
    return self._persist(OntologyObject(
        tenant_id=tenant_id,
        name=name,
        slug=slug,
        source_entity=source_entity,
        datasource_id=datasource_id,
        datasource_type=datasource_type,
        description=description,
        business_context=business_context,
        domain=domain,
        default_filters=default_filters or [],
    ))


def add_property(self, object_id: int, name: str, slug: str, data_type: str,
                 semantic_type: str = None, description: str = None,
                 is_computed: bool = False, expression: str = None) -> ObjectProperty:
    return self._persist(ObjectProperty(
        object_id=object_id,
        name=name,
        slug=slug,
        data_type=data_type,
        semantic_type=semantic_type,
        description=description,
        is_computed=is_computed,
        expression=expression,
    ))
```

```python
# backend/app/services/ontology/importer.py (inside import_dict)
from app.services.ontology.slug import ensure_unique_slug, slugify_name

existing_object_slugs = {obj.slug for obj in self.store.list_objects(tenant_id)}

for obj_def in ontology.get("objects", []):
    object_slug = ensure_unique_slug(slugify_name(obj_def["name"]), existing_object_slugs)
    existing_object_slugs.add(object_slug)
    obj = self.store.create_object(
        tenant_id=tenant_id,
        name=obj_def["name"],
        slug=object_slug,
        source_entity=source_entity,
        datasource_id=ds_id,
        datasource_type=ds_type,
        description=obj_def.get("description"),
        business_context=obj_def.get("business_context"),
        domain=obj_def.get("domain"),
        default_filters=obj_def.get("default_filters"),
    )

    property_slugs: set[str] = set()
    for prop in obj_def.get("properties", []):
        prop_slug = ensure_unique_slug(slugify_name(prop["name"]), property_slugs)
        property_slugs.add(prop_slug)
        self.store.add_property(
            object_id=obj.id,
            name=prop["name"],
            slug=prop_slug,
            data_type=prop.get("type", prop.get("data_type", "string")),
            semantic_type=prop.get("semantic_type"),
            description=prop.get("description"),
        )
```

- [ ] **Step 7: Run the slug unit test**

Run: `cd backend && source venv311/bin/activate && pytest tests/unit/ontology/test_slug.py -q`
Expected: `3 passed`

- [ ] **Step 8: Run the migration locally**

Run: `cd backend && source venv311/bin/activate && alembic upgrade head`
Expected: `Running upgrade ... -> <new_revision>, add slug to ontology`

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/ontology/ontology.py \
        backend/app/services/ontology/store.py \
        backend/app/services/ontology/importer.py \
        backend/app/services/ontology/slug.py \
        backend/alembic/versions/<new_revision>_add_slug_to_ontology.py \
        backend/tests/unit/ontology/test_slug.py
git commit -m "feat(agent): add ontology slugs for dynamic tool generation"
```

### Task 2: Add minimal ObjectSet core and compiler

**Files:**
- Create: `backend/app/services/agent/objectset/__init__.py`
- Create: `backend/app/services/agent/objectset/compiler.py`
- Test: `backend/tests/unit/agent/test_objectset.py`

- [ ] **Step 1: Write the failing ObjectSet tests**

```python
# backend/tests/unit/agent/test_objectset.py
from app.services.agent.objectset import Filter, ObjectSet, Sort
from app.services.agent.objectset.compiler import compile_query_args


def test_where_returns_new_objectset():
    base = ObjectSet(object_type="Product")
    updated = base.where(city="深圳")
    assert base is not updated
    assert base.filters == ()
    assert updated.filters == (Filter(field="city", operator="eq", value="深圳"),)


def test_compile_query_args_maps_eq_and_range():
    object_set = ObjectSet(
        object_type="Product",
        filters=(
            Filter(field="city", operator="eq", value="深圳"),
            Filter(field="price", operator="gte", value=20),
        ),
        selected=("sku", "price"),
        sort=(Sort(field="price", desc=True),),
        limit=10,
    )
    compiled = compile_query_args(object_set)
    assert compiled["object_type"] == "Product"
    assert compiled["selected_columns"] == ["sku", "price"]
    assert compiled["limit"] == 10
    assert compiled["filters"] == [
        {"field": "city", "operator": "=", "value": "深圳"},
        {"field": "price", "operator": ">=", "value": 20},
    ]
```

- [ ] **Step 2: Run the ObjectSet test to verify it fails**

Run: `cd backend && source venv311/bin/activate && pytest tests/unit/agent/test_objectset.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.agent.objectset'`

- [ ] **Step 3: Add the immutable ObjectSet types**

```python
# backend/app/services/agent/objectset/__init__.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Filter:
    field: str
    operator: str
    value: Any


@dataclass(frozen=True)
class Sort:
    field: str
    desc: bool = False


@dataclass(frozen=True)
class ObjectSet:
    object_type: str
    filters: tuple[Filter, ...] = ()
    selected: tuple[str, ...] = ()
    sort: tuple[Sort, ...] = ()
    limit: int | None = None

    def where(self, **conditions) -> "ObjectSet":
        new_filters = list(self.filters)
        for field, value in conditions.items():
            new_filters.append(Filter(field=field, operator="eq", value=value))
        return ObjectSet(
            object_type=self.object_type,
            filters=tuple(new_filters),
            selected=self.selected,
            sort=self.sort,
            limit=self.limit,
        )

    def select(self, *fields: str) -> "ObjectSet":
        return ObjectSet(
            object_type=self.object_type,
            filters=self.filters,
            selected=tuple(fields),
            sort=self.sort,
            limit=self.limit,
        )

    def order_by(self, field: str, desc: bool = False) -> "ObjectSet":
        return ObjectSet(
            object_type=self.object_type,
            filters=self.filters,
            selected=self.selected,
            sort=self.sort + (Sort(field=field, desc=desc),),
            limit=self.limit,
        )

    def limit_to(self, n: int) -> "ObjectSet":
        return ObjectSet(
            object_type=self.object_type,
            filters=self.filters,
            selected=self.selected,
            sort=self.sort,
            limit=n,
        )
```

- [ ] **Step 4: Add the compiler**

```python
# backend/app/services/agent/objectset/compiler.py
from __future__ import annotations

from app.services.agent.objectset import ObjectSet

_OPERATOR_MAP = {
    "eq": "=",
    "ne": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "contains": "LIKE",
    "in": "IN",
}


def compile_query_args(object_set: ObjectSet) -> dict:
    return {
        "object_type": object_set.object_type,
        "selected_columns": list(object_set.selected) or None,
        "filters": [
            {
                "field": item.field,
                "operator": _OPERATOR_MAP[item.operator],
                "value": item.value if item.operator != "contains" else str(item.value),
            }
            for item in object_set.filters
        ],
        "limit": object_set.limit,
    }
```

- [ ] **Step 5: Run the ObjectSet unit test**

Run: `cd backend && source venv311/bin/activate && pytest tests/unit/agent/test_objectset.py -q`
Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent/objectset/__init__.py \
        backend/app/services/agent/objectset/compiler.py \
        backend/tests/unit/agent/test_objectset.py
git commit -m "feat(agent): add immutable ObjectSet core"
```

### Task 3: Build derived query tools and ToolRegistryView

**Files:**
- Create: `backend/app/services/agent/tools/factory.py`
- Create: `backend/app/services/agent/tools/view.py`
- Modify: `backend/app/services/ontology/store.py:168-220`
- Test: `backend/tests/unit/agent/test_factory.py`
- Test: `backend/tests/unit/agent/test_view.py`

- [ ] **Step 1: Write the failing factory/view tests**

```python
# backend/tests/unit/agent/test_factory.py
from app.services.agent.tools.factory import ObjectTypeToolFactory


def test_factory_builds_search_and_count_tools():
    ontology = {
        "objects": [
            {
                "name": "商品",
                "slug": "product",
                "description": "商品主数据",
                "properties": [
                    {"name": "城市", "slug": "city", "type": "string", "semantic_type": None, "description": "门店城市"},
                    {"name": "价格", "slug": "price", "type": "float", "semantic_type": None, "description": "销售价格"},
                ],
            }
        ],
        "relationships": [],
    }
    specs = ObjectTypeToolFactory().build(ontology)
    names = {spec.name for spec in specs}
    assert names == {"search_product", "count_product"}
```

```python
# backend/tests/unit/agent/test_view.py
from app.services.agent.providers.base import ToolSpec
from app.services.agent.tools.registry import ToolRegistry
from app.services.agent.tools.view import ToolRegistryView


def test_view_matches_wildcard_specs():
    builtin = ToolRegistry()
    derived = [
        ToolSpec(name="search_product", description="", parameters={"type": "object", "properties": {}}),
        ToolSpec(name="count_product", description="", parameters={"type": "object", "properties": {}}),
    ]
    view = ToolRegistryView(builtin=builtin, derived=derived)
    specs = view.get_specs(["search_*", "count_*"])
    assert [spec.name for spec in specs] == ["search_product", "count_product"]
```

- [ ] **Step 2: Run the factory/view tests to verify they fail**

Run: `cd backend && source venv311/bin/activate && pytest tests/unit/agent/test_factory.py tests/unit/agent/test_view.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Extend ontology serialization with slug fields**

```python
# backend/app/services/ontology/store.py (inside get_full_ontology)
result.append({
    "name": obj.name,
    "slug": obj.slug,
    "source_entity": obj.source_entity,
    "datasource_id": obj.datasource_id,
    "description": obj.description,
    "business_context": obj.business_context,
    "domain": obj.domain,
    "properties": [
        {
            "name": p.name,
            "slug": p.slug,
            "type": p.data_type,
            "semantic_type": p.semantic_type,
            "description": p.description,
            "is_computed": p.is_computed,
        }
        for p in obj.properties
    ],
    # ...
})
```

- [ ] **Step 4: Add the derived tool factory**

```python
# backend/app/services/agent/tools/factory.py
from __future__ import annotations

from app.services.agent.providers.base import ToolSpec
from app.services.agent.objectset import ObjectSet, Filter
from app.services.agent.objectset.compiler import compile_query_args
from app.services.agent.tools.registry import ToolContext, ToolResult


class ObjectTypeToolFactory:
    def build(self, ontology: dict) -> list[ToolSpec]:
        specs: list[ToolSpec] = []
        for obj in ontology.get("objects", []):
            slug = obj["slug"]
            fields = obj.get("properties", [])
            properties = {
                "select": {
                    "type": "array",
                    "items": {"type": "string", "enum": [f["slug"] for f in fields]},
                    "description": f"可选字段: {', '.join(f'{f['name']}({f['slug']})' for f in fields)}",
                },
                "sort_by": {
                    "type": "string",
                    "enum": [f["slug"] for f in fields] + [f"{f['slug']}_desc" for f in fields],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 500},
            }
            for field in fields:
                field_slug = field["slug"]
                field_type = field["type"]
                properties[field_slug] = {"type": "string" if field_type == "string" else "number"}
                if field_type in {"integer", "float", "number"}:
                    properties[f"{field_slug}_min"] = {"type": "number"}
                    properties[f"{field_slug}_max"] = {"type": "number"}
                if field_type == "string":
                    properties[f"{field_slug}_contains"] = {"type": "string"}
            specs.append(ToolSpec(
                name=f"search_{slug}",
                description=f"查询对象 {obj['name']}（tool slug: {slug}）",
                parameters={"type": "object", "properties": properties},
            ))
            specs.append(ToolSpec(
                name=f"count_{slug}",
                description=f"统计对象 {obj['name']} 的数量（tool slug: {slug}）",
                parameters={"type": "object", "properties": {k: v for k, v in properties.items() if k not in {"select", "sort_by", "limit"}}},
            ))
        return specs
```

- [ ] **Step 5: Add ToolRegistryView**

```python
# backend/app/services/agent/tools/view.py
from __future__ import annotations

from app.services.agent.providers.base import ToolSpec
from app.services.agent.tools.registry import ToolContext, ToolRegistry, ToolResult
from app.services.agent.tools.factory import ObjectTypeToolFactory


class ToolRegistryView:
    def __init__(self, builtin: ToolRegistry, derived: list[ToolSpec]):
        self._builtin = builtin
        self._derived = {spec.name: spec for spec in derived}

    def _matches(self, pattern: str, name: str) -> bool:
        if pattern.endswith("*"):
            return name.startswith(pattern[:-1])
        return pattern == name

    def get_specs(self, whitelist: list[str] | None = None) -> list[ToolSpec]:
        all_specs = self._builtin.get_specs() + list(self._derived.values())
        if whitelist is None:
            return all_specs
        result: list[ToolSpec] = []
        for spec in all_specs:
            if any(self._matches(pattern, spec.name) for pattern in whitelist):
                result.append(spec)
        return result

    async def execute(self, name: str, params: dict, ctx: ToolContext) -> ToolResult:
        if self._builtin.has(name):
            return await self._builtin.execute(name, params, ctx)
        if name not in self._derived:
            return ToolResult(success=False, error=f"Unknown tool: {name}")
        return await self._execute_derived(name, params, ctx)
```

- [ ] **Step 6: Implement the derived handlers**

```python
# backend/app/services/agent/tools/view.py (add below __init__)
    async def _execute_derived(self, name: str, params: dict, ctx: ToolContext) -> ToolResult:
        if ctx.omaha_service is None:
            return ToolResult(success=False, error="OmahaService not available")

        object_slug = name.removeprefix("search_").removeprefix("count_")
        object_name = next(
            (obj["name"] for obj in ctx.ontology_context.get("objects", []) if obj.get("slug") == object_slug),
            object_slug,
        )

        filters = []
        for key, value in params.items():
            if value in (None, "", []):
                continue
            if key in {"select", "sort_by", "limit"}:
                continue
            if key.endswith("_min"):
                filters.append({"field": key[:-4], "operator": ">=", "value": value})
            elif key.endswith("_max"):
                filters.append({"field": key[:-4], "operator": "<=", "value": value})
            elif key.endswith("_contains"):
                filters.append({"field": key[:-9], "operator": "LIKE", "value": value})
            else:
                filters.append({"field": key, "operator": "=", "value": value})

        result = ctx.omaha_service.query_objects(
            object_type=object_name,
            selected_columns=params.get("select"),
            filters=filters or None,
            limit=params.get("limit", 100),
        )

        if name.startswith("count_") and result.get("success"):
            data = result.get("data") or []
            return ToolResult(success=True, data={"count": len(data), "data": data[:10]})
        return ToolResult(success=result.get("success", False), data=result, error=result.get("error"))
```

- [ ] **Step 7: Run the factory/view unit tests**

Run: `cd backend && source venv311/bin/activate && pytest tests/unit/agent/test_factory.py tests/unit/agent/test_view.py -q`
Expected: `2 passed`

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/ontology/store.py \
        backend/app/services/agent/tools/factory.py \
        backend/app/services/agent/tools/view.py \
        backend/tests/unit/agent/test_factory.py \
        backend/tests/unit/agent/test_view.py
git commit -m "feat(agent): derive per-object query tools per session"
```

### Task 4: Integrate per-turn tool views into ChatServiceV2 and ExecutorAgent

**Files:**
- Modify: `backend/app/services/agent/chat_service.py:17-26,63-125`
- Modify: `backend/app/services/agent/orchestrator/executor.py:46-90,112-118`
- Modify: `backend/app/services/agent/skills/definitions/data_query.yaml`

- [ ] **Step 1: Write the failing integration tests**

```python
# backend/tests/unit/agent/test_chat_refactor.py (add tests)
from app.services.agent.skills.loader import Skill


def test_data_query_skill_accepts_wildcards(loader):
    skill = loader.load("data_query")
    assert "search_*" in skill.allowed_tools
    assert "count_*" in skill.allowed_tools
```

```python
# backend/tests/unit/agent/test_executor.py (add test)
import pytest
from unittest.mock import AsyncMock
from app.services.agent.orchestrator.executor import ExecutorAgent
from app.services.agent.runtime.conversation import ConversationRuntime
from app.services.agent.skills.loader import Skill


@pytest.mark.asyncio
async def test_executor_uses_auto_on_first_turn():
    provider = AsyncMock()
    provider.send.return_value.tool_calls = []
    provider.send.return_value.content = "你好"
    provider.send.return_value.usage.input_tokens = 1
    provider.send.return_value.usage.output_tokens = 1
    registry = AsyncMock()
    registry.get_specs.return_value = []
    runtime = ConversationRuntime(Skill(name="data_query", description="", system_prompt="", allowed_tools=[]))
    runtime.append_user_message("你好")
    agent = ExecutorAgent(provider=provider, registry=registry)
    await agent.run(runtime, ctx=AsyncMock())
    assert provider.send.await_args.kwargs["tool_choice"] == "auto"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `cd backend && source venv311/bin/activate && pytest tests/unit/agent/test_executor.py tests/unit/agent/test_chat_refactor.py -q`
Expected: FAIL because first turn is still `required` and skill yaml lacks wildcards

- [ ] **Step 3: Update ChatServiceV2 to build a fresh view each turn**

```python
# backend/app/services/agent/chat_service.py (inside send_message)
from app.services.agent.tools.factory import ObjectTypeToolFactory
from app.services.agent.tools.view import ToolRegistryView
from app.services.legacy.financial.omaha import OmahaService

# ...
store = OntologyStore(self.db)
ontology_context = store.get_full_ontology(self.tenant_id)
factory = ObjectTypeToolFactory()
derived_specs = factory.build(ontology_context)
registry_view = ToolRegistryView(builtin=global_registry, derived=derived_specs)

ctx = ToolContext(
    db=self.db,
    omaha_service=self._build_omaha_service(),
    tenant_id=self.tenant_id,
    project_id=self.project.id,
    session_id=session_id,
    ontology_context=ontology_context,
)

executor = ExecutorAgent(provider=provider, registry=registry_view)
```

- [ ] **Step 4: Make ExecutorAgent first turn `auto`**

```python
# backend/app/services/agent/orchestrator/executor.py
for _iteration in range(self.max_iterations):
    if force_answer:
        tool_choice = "none"
    else:
        tool_choice = "auto"

    messages = runtime.get_messages_for_llm()
    llm_response = await self.provider.send(
        messages=messages,
        tools=tool_specs if has_tools else None,
        tool_choice=tool_choice,
    )
```

- [ ] **Step 5: Update the data query skill whitelist**

```yaml
# backend/app/services/agent/skills/definitions/data_query.yaml
name: data_query
description: 数据查询与分析
trigger_keywords: ["查询", "多少", "分析", "趋势", "对比", "统计", "报表"]
system_prompt: |
  你是数据分析专家。用户已完成数据建模，现在需要查询和分析业务数据。
  - 任何涉及具体数据的问题，必须先调用工具查询
  - 每个对象有自己的 search/count 工具，优先使用 `search_*` / `count_*`
  - 查询一次后立即基于结果回答，不要反复查询
  - 如果数据触发健康规则阈值，主动提醒
allowed_tools:
  - search_*
  - count_*
  - query_data
  - list_objects
  - get_schema
  - get_relationships
  - generate_chart
  - auto_chart
  - save_asset
  - list_assets
  - get_lineage
```

- [ ] **Step 6: Run the targeted unit tests**

Run: `cd backend && source venv311/bin/activate && pytest tests/unit/agent/test_executor.py tests/unit/agent/test_chat_refactor.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/agent/chat_service.py \
        backend/app/services/agent/orchestrator/executor.py \
        backend/app/services/agent/skills/definitions/data_query.yaml
git commit -m "feat(agent): wire per-turn derived tool views into chat runtime"
```

### Task 5: Expand end-to-end coverage and verify no regression

**Files:**
- Modify: `backend/tests/e2e/test_chat_scenarios_e2e.py`
- Modify: `backend/tests/e2e/test_multiturn_context_e2e.py`
- Test: existing E2E suites already in `backend/tests/e2e/`

- [ ] **Step 1: Add a failing derived-tool expectation to the E2E suite**

```python
# backend/tests/e2e/test_chat_scenarios_e2e.py (replace / extend assertions)
Scenario("filtered-query-cn", "查一下深圳的商品有哪些", ["深圳"], expect_tool_calls=True),
Scenario("filtered-multi", "深圳且价格大于 20 元的商品", ["深圳"], expect_tool_calls=True),
Scenario("unknown-field", "列出商品的 nonexistent_field 字段", [], expect_tool_calls=True),

# inside run_scenario()
tool_names = [tc.get("name", "") for tc in tool_calls]
if sc.name == "filtered-query-cn":
    assert any(name == "search_product" for name in tool_names)
```

- [ ] **Step 2: Add modeling-then-query and rename-then-query coverage**

```python
# backend/tests/e2e/test_multiturn_context_e2e.py (new conversation)
{
    "name": "rename-then-query",
    "turns": [
        ("把 Product 里的 city 字段改名成 location", []),
        ("列出 location 是深圳的商品", ["深圳"]),
    ],
}
```

- [ ] **Step 3: Run the targeted E2E scenario file before implementation is complete**

Run: `cd backend && source venv311/bin/activate && python tests/e2e/test_chat_scenarios_e2e.py`
Expected: FAIL on filtered-query-cn / filtered-multi because `search_product` does not exist yet

- [ ] **Step 4: Run the unit suites after implementation**

Run: `cd backend && source venv311/bin/activate && pytest tests/unit/ontology/test_slug.py tests/unit/agent/test_objectset.py tests/unit/agent/test_factory.py tests/unit/agent/test_view.py tests/unit/agent/test_executor.py -q`
Expected: PASS

- [ ] **Step 5: Run the main E2E suite**

Run: `cd backend && source venv311/bin/activate && python tests/e2e/test_chat_scenarios_e2e.py`
Expected: `filtered-query-cn`, `filtered-multi`, `unknown-field`, and baseline 21/25 all pass; report file written to `tests/e2e/e2e_report_<ts>.json`

- [ ] **Step 6: Run multi-turn E2E**

Run: `cd backend && source venv311/bin/activate && python tests/e2e/test_multiturn_context_e2e.py`
Expected: rename-then-query and existing correction flow pass; any remaining pronoun failures are documented but not introduced by this stage

- [ ] **Step 7: Run a direct smoke test against project 10**

Run: `cd backend && source venv311/bin/activate && python -c "
import asyncio, sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models.project import Project
from app.models.chat import ChatSession
from app.services.agent.chat_service import ChatServiceV2
async def main():
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == 10).first()
        session = ChatSession(project_id=10, user_id=project.owner_id, title='stage1 smoke')
        db.add(session); db.commit(); db.refresh(session)
        svc = ChatServiceV2(project=project, db=db)
        result = await svc.send_message(session.id, '查一下深圳的商品有哪些')
        print(result['message'])
    finally:
        db.close()
asyncio.run(main())
"`
Expected: human-readable answer with only 深圳 rows

- [ ] **Step 8: Commit**

```bash
git add backend/tests/e2e/test_chat_scenarios_e2e.py \
        backend/tests/e2e/test_multiturn_context_e2e.py
git commit -m "test(agent): cover derived per-object query tools end to end"
```

---

## Self-Review

### Spec coverage
- **Slug + constraints** → Task 1
- **ObjectSet central abstraction** → Task 2
- **Per-session derived tools** → Task 3
- **Wildcard whitelist / ToolRegistryView / first-turn auto** → Task 4
- **E2E acceptance criteria** → Task 5

No spec gaps remain.

### Placeholder scan
- No `TODO` / `TBD`
- Every task has exact files, tests, commands, expected output
- No "similar to Task N" references

### Type consistency
- Object slug is always `slug`
- Property slug is always `slug`
- Derived tools are always `search_<slug>` / `count_<slug>`
- `ToolRegistryView.get_specs()` is the single owner of wildcard expansion
- `ExecutorAgent` still receives a `registry` object with `get_specs()` and `execute()` methods
