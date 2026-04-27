# Link类型系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现Palantir Foundry风格的Link类型系统，支持跨数据源关系定义、自动JOIN展开、反向导航和链式导航

**Architecture:** 四层架构 - Tool Layer（动态工具生成）→ Link Engine（Link解析/展开/导航）→ Data Access Layer（统一数据源接口）→ Data Sources

**Tech Stack:** Python 3.11, SQLAlchemy, FastAPI, pytest

---

## File Structure

### New Files
- `backend/app/services/agent/link/__init__.py` - Link引擎包
- `backend/app/services/agent/link/resolver.py` - LinkResolver（解析Link定义）
- `backend/app/services/agent/link/expander.py` - LinkExpander（展开Link字段）
- `backend/app/services/agent/link/navigator.py` - PathNavigator（多跳导航）
- `backend/app/services/agent/tools/builtin/navigate.py` - navigate_path工具定义
- `backend/alembic/versions/002_add_link_type.py` - 数据库migration
- `backend/tests/unit/agent/link/test_resolver.py` - LinkResolver测试
- `backend/tests/unit/agent/link/test_expander.py` - LinkExpander测试
- `backend/tests/unit/agent/link/test_navigator.py` - PathNavigator测试
- `backend/tests/integration/test_link_e2e.py` - Link集成测试

### Modified Files
- `backend/app/models/ontology/ontology.py` - 添加Link字段到ObjectProperty
- `backend/app/services/ontology/store.py` - add_property支持Link类型
- `backend/app/services/ontology/importer.py` - 两阶段导入
- `backend/app/services/agent/tools/factory.py` - 生成反向导航工具
- `backend/app/services/agent/tools/view.py` - 集成LinkExpander，执行反向导航
- `backend/app/services/agent/tools/registry.py` - 注册navigate_path工具

---

## Week 1: Link基础

### Task 1: 数据库Schema扩展

**Files:**
- Modify: `backend/app/models/ontology/ontology.py:40-62`
- Create: `backend/alembic/versions/002_add_link_type.py`

- [ ] **Step 1: 添加Link字段到ObjectProperty模型**

```python
# backend/app/models/ontology/ontology.py
class ObjectProperty(Base):
    __tablename__ = "object_properties"
    
    # ... 现有字段 ...
    
    # Link类型专用字段（新增）
    link_target_id = Column(Integer, ForeignKey("ontology_objects.id"))
    link_foreign_key = Column(String)
    link_target_key = Column(String, default="id")
    
    # 关系
    link_target = relationship("OntologyObject", foreign_keys=[link_target_id])
```

- [ ] **Step 2: 创建数据库migration**

```python
# backend/alembic/versions/002_add_link_type.py
"""Add Link type support

Revision ID: 002_add_link_type
Revises: 001_add_ontology_slugs
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    with op.batch_alter_table('object_properties', schema=None) as batch_op:
        batch_op.add_column(sa.Column('link_target_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('link_foreign_key', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('link_target_key', sa.String(), nullable=True))
        batch_op.create_foreign_key(
            'fk_property_link_target',
            'ontology_objects',
            ['link_target_id'],
            ['id']
        )

def downgrade():
    with op.batch_alter_table('object_properties', schema=None) as batch_op:
        batch_op.drop_constraint('fk_property_link_target', type_='foreignkey')
        batch_op.drop_column('link_target_key')
        batch_op.drop_column('link_foreign_key')
        batch_op.drop_column('link_target_id')
```

- [ ] **Step 3: 运行migration**

Run: `cd backend && alembic upgrade head`
Expected: Migration成功，object_properties表新增3个字段

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/ontology/ontology.py backend/alembic/versions/002_add_link_type.py
git commit -m "feat(ontology): add Link type support to ObjectProperty model"
```

---

### Task 2: OntologyStore支持Link类型

**Files:**
- Modify: `backend/app/services/ontology/store.py:60-90`
- Test: `backend/tests/unit/ontology/test_store.py`

- [ ] **Step 1: 写测试 - add_property支持Link类型**

```python
# backend/tests/unit/ontology/test_store.py
def test_add_link_property(db_session, tenant):
    store = OntologyStore(db_session)
    
    # 创建两个对象
    category = store.create_object(tenant.id, "Category", "category", "mysql", "mysql_db")
    sku = store.create_object(tenant.id, "SKU", "sku", "mysql", "mysql_db")
    
    # 添加Link属性
    link_prop = store.add_property(
        object_id=sku.id,
        name="类目",
        slug="category",
        data_type="link",
        link_target="Category",
        link_foreign_key="category_id",
        link_target_key="category_id"
    )
    
    assert link_prop.data_type == "link"
    assert link_prop.link_target_id == category.id
    assert link_prop.link_foreign_key == "category_id"
    assert link_prop.link_target_key == "category_id"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/unit/ontology/test_store.py::test_add_link_property -v`
Expected: FAIL - add_property不接受link_target参数

- [ ] **Step 3: 实现 - 扩展add_property方法**

```python
# backend/app/services/ontology/store.py
def add_property(
    self,
    object_id: int,
    name: str,
    data_type: str,
    slug: str = None,
    semantic_type: str = None,
    description: str = None,
    # Link类型参数
    link_target: str = None,
    link_foreign_key: str = None,
    link_target_key: str = "id",
) -> ObjectProperty:
    """添加属性（支持Link类型）"""
    
    if slug is None:
        from app.services.ontology.slug import slugify_name, ensure_unique_slug
        base_slug = slugify_name(name)
        slug = ensure_unique_slug(
            self.db, base_slug, "object_properties", "slug",
            object_id=object_id
        )
    
    # 如果是Link类型，解析目标对象
    link_target_id = None
    if data_type == "link":
        if not link_target or not link_foreign_key:
            raise ValueError("Link类型必须指定target和foreign_key")
        
        # 查找目标对象
        tenant_id = self.db.query(OntologyObject.tenant_id).filter(
            OntologyObject.id == object_id
        ).scalar()
        
        target_obj = self.db.query(OntologyObject).filter(
            OntologyObject.tenant_id == tenant_id,
            OntologyObject.name == link_target
        ).first()
        
        if not target_obj:
            raise ValueError(f"目标对象 '{link_target}' 不存在")
        
        link_target_id = target_obj.id
    
    prop = ObjectProperty(
        object_id=object_id,
        name=name,
        slug=slug,
        data_type=data_type,
        semantic_type=semantic_type,
        description=description,
        link_target_id=link_target_id,
        link_foreign_key=link_foreign_key,
        link_target_key=link_target_key,
    )
    
    self.db.add(prop)
    self.db.flush()
    return prop
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest backend/tests/unit/ontology/test_store.py::test_add_link_property -v`
Expected: PASS

- [ ] **Step 5: 测试自引用Link**

```python
def test_add_self_referencing_link(db_session, tenant):
    store = OntologyStore(db_session)
    category = store.create_object(tenant.id, "Category", "category", "mysql", "mysql_db")
    
    # 自引用Link
    parent_prop = store.add_property(
        object_id=category.id,
        name="父类目",
        slug="parent",
        data_type="link",
        link_target="Category",
        link_foreign_key="parent_id",
        link_target_key="category_id"
    )
    
    assert parent_prop.link_target_id == category.id
```

Run: `pytest backend/tests/unit/ontology/test_store.py::test_add_self_referencing_link -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ontology/store.py backend/tests/unit/ontology/test_store.py
git commit -m "feat(ontology): add Link type support to OntologyStore.add_property"
```

---

### Task 3: OntologyImporter两阶段导入

**Files:**
- Modify: `backend/app/services/ontology/importer.py:20-123`
- Test: `backend/tests/unit/ontology/test_importer.py`

- [ ] **Step 1: 写测试 - 导入包含Link的本体**

```python
# backend/tests/unit/ontology/test_importer.py
def test_import_ontology_with_links(db_session, tenant):
    importer = OntologyImporter(db_session)
    
    config = {
        "datasources": [{"id": "mysql_db", "type": "mysql"}],
        "ontology": {
            "objects": [
                {
                    "name": "Category",
                    "slug": "category",
                    "datasource": "mysql_db",
                    "properties": [
                        {"name": "类目ID", "slug": "category_id", "type": "string"}
                    ]
                },
                {
                    "name": "SKU",
                    "slug": "sku",
                    "datasource": "mysql_db",
                    "properties": [
                        {"name": "SKU编码", "slug": "sku_id", "type": "string"},
                        {
                            "name": "类目",
                            "slug": "category",
                            "type": "link",
                            "target": "Category",
                            "foreign_key": "category_id"
                        }
                    ]
                }
            ]
        }
    }
    
    result = importer.import_dict(tenant.id, config)
    
    assert result["objects_created"] == 2
    
    # 验证Link属性
    sku = importer.store.get_object(tenant.id, "SKU")
    link_prop = next(p for p in sku.properties if p.slug == "category")
    assert link_prop.data_type == "link"
    assert link_prop.link_target.name == "Category"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/unit/ontology/test_importer.py::test_import_ontology_with_links -v`
Expected: FAIL - importer不支持Link类型

- [ ] **Step 3: 实现 - 两阶段导入**

```python
# backend/app/services/ontology/importer.py
def import_dict(self, tenant_id: int, config: dict) -> dict:
    ontology = config.get("ontology", {})
    datasources_list = config.get("datasources", [])
    datasources = {ds["id"]: ds for ds in datasources_list}
    
    objects_created = 0
    objects_updated = 0
    object_map = {}
    
    # 阶段1: 创建对象 + 非Link属性
    for obj_def in ontology.get("objects", []):
        ds_id = obj_def.get("datasource", "")
        ds_type = datasources.get(ds_id, {}).get("type", "unknown")
        source_entity = obj_def.get("source_entity") or obj_def.get("api_name", "")
        
        existing = self.store.get_object(tenant_id, obj_def["name"])
        if existing:
            self.store.delete_object(tenant_id, obj_def["name"])
            objects_updated += 1
        else:
            objects_created += 1
        
        obj = self.store.create_object(
            tenant_id=tenant_id,
            name=obj_def["name"],
            source_entity=source_entity,
            datasource_id=ds_id,
            datasource_type=ds_type,
            description=obj_def.get("description"),
        )
        object_map[obj_def["name"]] = obj
        
        # 只添加非Link属性
        for prop in obj_def.get("properties", []):
            if prop.get("type") != "link":
                self.store.add_property(
                    object_id=obj.id,
                    name=prop["name"],
                    data_type=prop.get("type", "string"),
                    semantic_type=prop.get("semantic_type"),
                    description=prop.get("description"),
                )
    
    # 阶段2: 添加Link属性
    for obj_def in ontology.get("objects", []):
        obj = object_map[obj_def["name"]]
        for prop in obj_def.get("properties", []):
            if prop.get("type") == "link":
                self.store.add_property(
                    object_id=obj.id,
                    name=prop["name"],
                    data_type="link",
                    link_target=prop["target"],
                    link_foreign_key=prop["foreign_key"],
                    link_target_key=prop.get("target_key", "id"),
                )
    
    self.db.commit()
    return {
        "objects_created": objects_created,
        "objects_updated": objects_updated,
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest backend/tests/unit/ontology/test_importer.py::test_import_ontology_with_links -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ontology/importer.py backend/tests/unit/ontology/test_importer.py
git commit -m "feat(ontology): support Link type in OntologyImporter with two-phase import"
```

---

### Task 4: LinkResolver实现

**Files:**
- Create: `backend/app/services/agent/link/__init__.py`
- Create: `backend/app/services/agent/link/resolver.py`
- Create: `backend/tests/unit/agent/link/test_resolver.py`

- [ ] **Step 1: 创建Link包**

```python
# backend/app/services/agent/link/__init__.py
"""Link引擎 - 解析、展开、导航Link关系"""
from .resolver import LinkResolver, LinkDefinition
from .expander import LinkExpander
from .navigator import PathNavigator

__all__ = ["LinkResolver", "LinkDefinition", "LinkExpander", "PathNavigator"]
```

- [ ] **Step 2: 写测试 - LinkResolver解析Link定义**

```python
# backend/tests/unit/agent/link/test_resolver.py
import pytest
from app.services.agent.link.resolver import LinkResolver

@pytest.fixture
def sample_ontology():
    return {
        "objects": [
            {
                "name": "Category",
                "slug": "category",
                "datasource_type": "mysql",
                "datasource_id": "mysql_db",
                "properties": [
                    {"name": "类目ID", "slug": "category_id", "type": "string"}
                ]
            },
            {
                "name": "SKU",
                "slug": "sku",
                "datasource_type": "mysql",
                "datasource_id": "mysql_db",
                "properties": [
                    {"name": "SKU编码", "slug": "sku_id", "type": "string"},
                    {
                        "name": "类目",
                        "slug": "category",
                        "type": "link",
                        "link": {
                            "target": "Category",
                            "target_slug": "category",
                            "foreign_key": "category_id",
                            "target_key": "category_id"
                        }
                    }
                ]
            }
        ]
    }

def test_resolve_link(sample_ontology):
    resolver = LinkResolver()
    
    link_def = resolver.resolve_link("SKU", "category", sample_ontology)
    
    assert link_def is not None
    assert link_def.source_object == "SKU"
    assert link_def.source_slug == "sku"
    assert link_def.link_field == "category"
    assert link_def.target_object == "Category"
    assert link_def.target_slug == "category"
    assert link_def.foreign_key == "category_id"
    assert link_def.target_key == "category_id"
    assert link_def.datasource_type == "mysql"

def test_resolve_non_link_field(sample_ontology):
    resolver = LinkResolver()
    
    link_def = resolver.resolve_link("SKU", "sku_id", sample_ontology)
    
    assert link_def is None
```

- [ ] **Step 3: 运行测试确认失败**

Run: `pytest backend/tests/unit/agent/link/test_resolver.py -v`
Expected: FAIL - LinkResolver不存在

- [ ] **Step 4: 实现LinkResolver**

```python
# backend/app/services/agent/link/resolver.py
from typing import Optional
from dataclasses import dataclass

@dataclass
class LinkDefinition:
    """Link定义（解析后的结构）"""
    source_object: str
    source_slug: str
    link_field: str
    target_object: str
    target_slug: str
    foreign_key: str
    target_key: str
    datasource_type: str
    datasource_id: str


class LinkResolver:
    """解析Link定义"""
    
    def resolve_link(
        self,
        object_name: str,
        link_field_slug: str,
        ontology: dict
    ) -> Optional[LinkDefinition]:
        """解析Link定义"""
        source_obj = self._find_object(ontology, object_name)
        if not source_obj:
            raise ValueError(f"对象 '{object_name}' 不存在")
        
        link_prop = next(
            (p for p in source_obj["properties"] if p["slug"] == link_field_slug),
            None
        )
        
        if not link_prop or link_prop["type"] != "link":
            return None
        
        target_name = link_prop["link"]["target"]
        target_obj = self._find_object(ontology, target_name)
        if not target_obj:
            raise ValueError(f"目标对象 '{target_name}' 不存在")
        
        return LinkDefinition(
            source_object=object_name,
            source_slug=source_obj["slug"],
            link_field=link_field_slug,
            target_object=target_obj["name"],
            target_slug=target_obj["slug"],
            foreign_key=link_prop["link"]["foreign_key"],
            target_key=link_prop["link"].get("target_key", "id"),
            datasource_type=target_obj["datasource_type"],
            datasource_id=target_obj["datasource_id"],
        )
    
    def _find_object(self, ontology: dict, name: str) -> Optional[dict]:
        return next(
            (obj for obj in ontology["objects"] if obj["name"] == name),
            None
        )
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest backend/tests/unit/agent/link/test_resolver.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent/link/ backend/tests/unit/agent/link/
git commit -m "feat(link): implement LinkResolver for parsing Link definitions"
```

---

### Task 5: LinkExpander实现

**Files:**
- Create: `backend/app/services/agent/link/expander.py`
- Create: `backend/tests/unit/agent/link/test_expander.py`

- [ ] **Step 1: 写测试 - LinkExpander展开Link字段**

```python
# backend/tests/unit/agent/link/test_expander.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.agent.link.expander import LinkExpander
from app.services.agent.link.resolver import LinkResolver

@pytest.fixture
def sample_ontology():
    return {
        "objects": [
            {
                "name": "Category",
                "slug": "category",
                "properties": [{"name": "类目ID", "slug": "category_id", "type": "string"}]
            },
            {
                "name": "SKU",
                "slug": "sku",
                "properties": [
                    {"name": "SKU编码", "slug": "sku_id", "type": "string"},
                    {
                        "name": "类目",
                        "slug": "category",
                        "type": "link",
                        "link": {
                            "target": "Category",
                            "foreign_key": "category_id",
                            "target_key": "category_id"
                        }
                    }
                ]
            }
        ]
    }

@pytest.mark.asyncio
async def test_expand_links(sample_ontology):
    resolver = LinkResolver()
    expander = LinkExpander(resolver)
    
    # Mock context
    ctx = MagicMock()
    ctx.omaha_service.query_objects = AsyncMock(return_value={
        "success": True,
        "data": [{"category_id": "123", "name": "手机"}]
    })
    
    # 输入数据
    rows = [
        {"sku_id": "A001", "name": "iPhone 15", "category_id": "123"}
    ]
    
    # 展开Link
    result = await expander.expand_links(rows, "SKU", sample_ontology, ctx)
    
    # 验证
    assert result[0]["category"] == {"category_id": "123", "name": "手机"}
    ctx.omaha_service.query_objects.assert_called_once()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/unit/agent/link/test_expander.py -v`
Expected: FAIL - LinkExpander不存在

- [ ] **Step 3: 实现LinkExpander**

```python
# backend/app/services/agent/link/expander.py
from typing import Optional
from app.services.agent.link.resolver import LinkResolver, LinkDefinition
from app.services.agent.tools.registry import ToolContext

class LinkExpander:
    """展开Link字段（极简版：无缓存，无批量优化）"""
    
    def __init__(self, resolver: LinkResolver):
        self.resolver = resolver
    
    async def expand_links(
        self,
        rows: list[dict],
        object_name: str,
        ontology: dict,
        ctx: ToolContext
    ) -> list[dict]:
        """自动展开所有Link字段"""
        if not rows:
            return rows
        
        obj_def = next(
            (o for o in ontology["objects"] if o["name"] == object_name),
            None
        )
        if not obj_def:
            return rows
        
        link_fields = [
            p for p in obj_def["properties"]
            if p["type"] == "link"
        ]
        
        for link_prop in link_fields:
            link_def = self.resolver.resolve_link(
                object_name,
                link_prop["slug"],
                ontology
            )
            
            if link_def:
                await self._expand_one_link(rows, link_def, ctx)
        
        return rows
    
    async def _expand_one_link(
        self,
        rows: list[dict],
        link_def: LinkDefinition,
        ctx: ToolContext
    ):
        """展开单个Link字段（极简：逐行查询）"""
        for row in rows:
            fk_value = row.get(link_def.foreign_key)
            if fk_value is None:
                continue
            
            target_obj = await self._fetch_target_object(
                link_def, fk_value, ctx
            )
            
            if target_obj:
                row[link_def.link_field] = target_obj
    
    async def _fetch_target_object(
        self,
        link_def: LinkDefinition,
        fk_value: any,
        ctx: ToolContext
    ) -> Optional[dict]:
        """查询目标对象"""
        result = ctx.omaha_service.query_objects(
            object_type=link_def.target_object,
            filters=[{
                "field": link_def.target_key,
                "operator": "=",
                "value": fk_value
            }],
            limit=1
        )
        
        if result.get("success") and result.get("data"):
            return result["data"][0]
        
        return None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest backend/tests/unit/agent/link/test_expander.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent/link/expander.py backend/tests/unit/agent/link/test_expander.py
git commit -m "feat(link): implement LinkExpander for auto-expanding Link fields"
```

---

### Task 6: 集成LinkExpander到ToolRegistryView

**Files:**
- Modify: `backend/app/services/agent/tools/view.py:31-40,200-230`

- [ ] **Step 1: 写测试 - search工具自动展开Link**

```python
# backend/tests/unit/agent/test_view.py (添加到现有文件)
@pytest.mark.asyncio
async def test_search_tool_expands_links():
    # 准备本体（包含Link）
    ontology = {
        "objects": [
            {
                "name": "Category",
                "slug": "category",
                "properties": [{"name": "类目ID", "slug": "category_id", "type": "string"}]
            },
            {
                "name": "SKU",
                "slug": "sku",
                "properties": [
                    {"name": "SKU编码", "slug": "sku_id", "type": "string"},
                    {
                        "name": "类目",
                        "slug": "category",
                        "type": "link",
                        "link": {"target": "Category", "foreign_key": "category_id", "target_key": "category_id"}
                    }
                ]
            }
        ]
    }
    
    # Mock OmahaService
    omaha_service = MagicMock()
    omaha_service.query_objects = MagicMock(side_effect=[
        # 第1次调用：查询SKU
        {"success": True, "data": [{"sku_id": "A001", "category_id": "123"}]},
        # 第2次调用：查询Category（展开Link）
        {"success": True, "data": [{"category_id": "123", "name": "手机"}]}
    ])
    
    # 执行查询
    view = ToolRegistryView(builtin=MagicMock(), derived=[])
    ctx = ToolContext(omaha_service=omaha_service, ontology_context={"ontology": ontology})
    
    result = await view._execute_derived("search_sku", {"sku_id": "A001"}, ctx)
    
    # 验证Link已展开
    assert result.success
    assert result.data["data"][0]["category"] == {"category_id": "123", "name": "手机"}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/unit/agent/test_view.py::test_search_tool_expands_links -v`
Expected: FAIL - Link字段未展开

- [ ] **Step 3: 集成LinkExpander**

```python
# backend/app/services/agent/tools/view.py
from app.services.agent.link import LinkResolver, LinkExpander

class ToolRegistryView:
    
    def __init__(self, builtin: ToolRegistry, derived: list[ToolSpec]):
        self.builtin = builtin
        self.derived = derived
        self._derived_by_name = {spec.name: spec for spec in derived}
        
        # 新增：Link组件
        self.link_resolver = LinkResolver()
        self.link_expander = LinkExpander(self.link_resolver)
    
    async def _execute_derived(self, name: str, params: dict, ctx: ToolContext) -> ToolResult:
        # ... 现有查询逻辑 ...
        
        result = ctx.omaha_service.query_objects(
            object_type=object_name,
            selected_columns=selected_columns,
            filters=filters,
            limit=limit,
        )
        
        if not result.get("success"):
            return ToolResult(success=False, error=result.get("error"))
        
        # 新增：自动展开Link字段
        rows = result.get("data", [])
        if rows:
            ontology = ctx.ontology_context.get("ontology", {})
            rows = await self.link_expander.expand_links(
                rows, object_name, ontology, ctx
            )
            result["data"] = rows
        
        # ... 其余逻辑 ...
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest backend/tests/unit/agent/test_view.py::test_search_tool_expands_links -v`
Expected: PASS

- [ ] **Step 5: 运行所有agent测试**

Run: `pytest backend/tests/unit/agent/ -v`
Expected: 所有测试通过

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent/tools/view.py backend/tests/unit/agent/test_view.py
git commit -m "feat(link): integrate LinkExpander into ToolRegistryView for auto-expansion"
```

---

## Week 2: 反向导航

### Task 7: 反向导航工具生成

**Files:**
- Modify: `backend/app/services/agent/tools/factory.py:70-120`
- Test: `backend/tests/unit/agent/test_factory.py`

- [ ] **Step 1: 写测试 - 生成反向导航工具**

```python
# backend/tests/unit/agent/test_factory.py (添加)
def test_factory_generates_reverse_nav_tools():
    ontology = {
        "objects": [
            {
                "name": "Category",
                "slug": "category",
                "properties": [{"name": "类目ID", "slug": "category_id", "type": "string"}]
            },
            {
                "name": "SKU",
                "slug": "sku",
                "properties": [
                    {
                        "name": "类目",
                        "slug": "category",
                        "type": "link",
                        "link": {"target": "Category", "foreign_key": "category_id"}
                    }
                ]
            }
        ]
    }
    
    tools = ObjectTypeToolFactory.build(ontology)
    tool_names = {t.name for t in tools}
    
    # 应该生成反向导航工具
    assert "get_category_skus" in tool_names
    
    # 验证工具schema
    reverse_tool = next(t for t in tools if t.name == "get_category_skus")
    assert "category_id" in reverse_tool.parameters["properties"]
    assert "limit" in reverse_tool.parameters["properties"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/unit/agent/test_factory.py::test_factory_generates_reverse_nav_tools -v`
Expected: FAIL - 未生成反向导航工具

- [ ] **Step 3: 实现反向导航工具生成**

```python
# backend/app/services/agent/tools/factory.py
from app.services.ontology.slug import slugify_name

class ObjectTypeToolFactory:
    
    @staticmethod
    def build(ontology: dict) -> list[ToolSpec]:
        tools = []
        
        # 原有工具：search_*/count_*/aggregate_*
        for obj in ontology["objects"]:
            tools.extend([
                ObjectTypeToolFactory._build_search_tool(obj),
                ObjectTypeToolFactory._build_count_tool(obj),
                ObjectTypeToolFactory._build_aggregate_tool(obj),
            ])
        
        # 新增：反向导航工具
        for obj in ontology["objects"]:
            for prop in obj.get("properties", []):
                if prop.get("type") == "link":
                    tools.append(
                        ObjectTypeToolFactory._build_reverse_nav_tool(obj, prop)
                    )
        
        return tools
    
    @staticmethod
    def _build_reverse_nav_tool(source_obj: dict, link_prop: dict) -> ToolSpec:
        """生成反向导航工具"""
        target_name = link_prop["link"]["target"]
        target_slug = slugify_name(target_name)
        source_slug = source_obj["slug"]
        
        tool_name = f"get_{target_slug}_{source_slug}s"
        
        params = {
            "type": "object",
            "properties": {
                f"{target_slug}_id": {
                    "type": "string",
                    "description": f"ID of the {target_name}"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results"
                }
            },
            "required": [f"{target_slug}_id"],
            "additionalProperties": False
        }
        
        return ToolSpec(
            name=tool_name,
            description=f"Get all {source_obj['name']} objects linked to a {target_name}",
            parameters=params
        )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest backend/tests/unit/agent/test_factory.py::test_factory_generates_reverse_nav_tools -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent/tools/factory.py backend/tests/unit/agent/test_factory.py
git commit -m "feat(link): generate reverse navigation tools in ObjectTypeToolFactory"
```

---

### Task 8: 反向导航执行逻辑

**Files:**
- Modify: `backend/app/services/agent/tools/view.py:100-180`
- Test: `backend/tests/unit/agent/test_view.py`

- [ ] **Step 1: 写测试 - 执行反向导航**

```python
# backend/tests/unit/agent/test_view.py
@pytest.mark.asyncio
async def test_execute_reverse_nav():
    ontology = {
        "objects": [
            {
                "name": "Category",
                "slug": "category",
                "properties": [{"name": "类目ID", "slug": "category_id", "type": "string"}]
            },
            {
                "name": "SKU",
                "slug": "sku",
                "properties": [
                    {
                        "name": "类目",
                        "slug": "category",
                        "type": "link",
                        "link": {"target": "Category", "foreign_key": "category_id", "target_key": "category_id"}
                    }
                ]
            }
        ]
    }
    
    omaha_service = MagicMock()
    omaha_service.query_objects = MagicMock(return_value={
        "success": True,
        "data": [
            {"sku_id": "A001", "name": "iPhone 15", "category_id": "123"},
            {"sku_id": "A002", "name": "iPhone 14", "category_id": "123"}
        ]
    })
    
    view = ToolRegistryView(builtin=MagicMock(), derived=[])
    ctx = ToolContext(omaha_service=omaha_service, ontology_context={"ontology": ontology})
    
    result = await view.execute("get_category_skus", {"category_id": "123"}, ctx)
    
    assert result.success
    assert len(result.data["data"]) == 2
    omaha_service.query_objects.assert_called_with(
        object_type="SKU",
        filters=[{"field": "category_id", "operator": "=", "value": "123"}],
        limit=None
    )
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/unit/agent/test_view.py::test_execute_reverse_nav -v`
Expected: FAIL - 未识别反向导航工具

- [ ] **Step 3: 实现反向导航执行**

```python
# backend/app/services/agent/tools/view.py
class ToolRegistryView:
    
    async def execute(self, name: str, params: dict, ctx: ToolContext) -> ToolResult:
        if name == "refine_objectset":
            return await self._execute_refine(params, ctx)
        elif name.startswith("get_") and "_" in name[4:]:
            # 检查是否是反向导航工具
            return await self._execute_reverse_nav(name, params, ctx)
        elif self.builtin.has(name):
            return await self.builtin.execute(name, params, ctx)
        elif name in self._derived_by_name:
            return await self._execute_derived(name, params, ctx)
        else:
            return ToolResult(success=False, error=f"Unknown tool: {name}")
    
    async def _execute_reverse_nav(
        self, 
        name: str, 
        params: dict, 
        ctx: ToolContext
    ) -> ToolResult:
        """执行反向导航"""
        try:
            # 解析工具名：get_category_skus → target=category, source=sku
            parts = name[4:].rsplit("_", 1)
            if len(parts) != 2:
                return ToolResult(success=False, error=f"Invalid tool name: {name}")
            
            target_slug = parts[0]
            source_slug = parts[1].rstrip("s")
            
            # 查找源对象和Link定义
            ontology = ctx.ontology_context.get("ontology", {})
            source_obj = next(
                (o for o in ontology["objects"] if o["slug"] == source_slug),
                None
            )
            if not source_obj:
                return ToolResult(success=False, error=f"Object '{source_slug}' not found")
            
            # 查找Link字段
            link_prop = None
            for prop in source_obj["properties"]:
                if prop.get("type") == "link":
                    from app.services.ontology.slug import slugify_name
                    link_target_slug = slugify_name(prop["link"]["target"])
                    if link_target_slug == target_slug:
                        link_prop = prop
                        break
            
            if not link_prop:
                return ToolResult(
                    success=False,
                    error=f"No link from {source_slug} to {target_slug}"
                )
            
            # 构建反向查询
            target_id = params.get(f"{target_slug}_id")
            foreign_key = link_prop["link"]["foreign_key"]
            
            result = ctx.omaha_service.query_objects(
                object_type=source_obj["name"],
                filters=[{
                    "field": foreign_key,
                    "operator": "=",
                    "value": target_id
                }],
                limit=params.get("limit")
            )
            
            if not result.get("success"):
                return ToolResult(success=False, error=result.get("error"))
            
            # 自动展开Link字段
            rows = result.get("data", [])
            if rows:
                rows = await self.link_expander.expand_links(
                    rows, source_obj["name"], ontology, ctx
                )
                result["data"] = rows
            
            return ToolResult(success=True, data=result)
        
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest backend/tests/unit/agent/test_view.py::test_execute_reverse_nav -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent/tools/view.py backend/tests/unit/agent/test_view.py
git commit -m "feat(link): implement reverse navigation execution in ToolRegistryView"
```

---

### Task 9: E2E测试 - 反向导航

**Files:**
- Create: `backend/tests/e2e/test_link_scenarios.py`

- [ ] **Step 1: 创建E2E测试场景**

```python
# backend/tests/e2e/test_link_scenarios.py
import pytest
from app.services.agent.chat_service import ChatService

@pytest.mark.asyncio
async def test_reverse_navigation_scenario(db_session, tenant, sample_ontology_with_links):
    """
    场景：用户问"手机类目下有哪些商品？"
    预期：LLM调用 get_category_skus 工具
    """
    chat_service = ChatService(db_session)
    
    # 创建会话
    session = chat_service.create_session(
        tenant_id=tenant.id,
        ontology_id=sample_ontology_with_links.id
    )
    
    # 用户提问
    response = await chat_service.send_message(
        session_id=session.id,
        user_message="手机类目下有哪些商品？"
    )
    
    # 验证
    assert response["success"]
    assert "iPhone" in response["message"] or "商品" in response["message"]
    
    # 验证工具调用
    tool_calls = response.get("tool_calls", [])
    assert any("get_category" in call["name"] for call in tool_calls)
```

- [ ] **Step 2: 运行E2E测试**

Run: `pytest backend/tests/e2e/test_link_scenarios.py::test_reverse_navigation_scenario -v -s`
Expected: PASS（如果LLM可用）或 SKIP（如果无LLM）

- [ ] **Step 3: Commit**

```bash
git add backend/tests/e2e/test_link_scenarios.py
git commit -m "test(link): add E2E test for reverse navigation scenario"
```

---

## Week 3: 多跳导航

### Task 10: PathNavigator实现

**Files:**
- Create: `backend/app/services/agent/link/navigator.py`
- Create: `backend/tests/unit/agent/link/test_navigator.py`

- [ ] **Step 1: 写测试 - 单跳导航**

```python
# backend/tests/unit/agent/link/test_navigator.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.agent.link.navigator import PathNavigator
from app.services.agent.link.resolver import LinkResolver

@pytest.fixture
def sample_ontology():
    return {
        "objects": [
            {
                "name": "Category",
                "slug": "category",
                "properties": [{"name": "类目ID", "slug": "category_id", "type": "string"}]
            },
            {
                "name": "SKU",
                "slug": "sku",
                "properties": [
                    {
                        "name": "类目",
                        "slug": "category",
                        "type": "link",
                        "link": {"target": "Category", "foreign_key": "category_id", "target_key": "category_id"}
                    }
                ]
            }
        ]
    }

@pytest.mark.asyncio
async def test_navigate_single_hop(sample_ontology):
    resolver = LinkResolver()
    navigator = PathNavigator(resolver)
    
    # Mock context
    ctx = MagicMock()
    ctx.ontology_context = {"ontology": sample_ontology}
    ctx.omaha_service.query_objects = AsyncMock(side_effect=[
        # 第1次：查询起点Category
        {"success": True, "data": [{"category_id": "123", "name": "手机"}]},
        # 第2次：反向查询SKU
        {"success": True, "data": [
            {"sku_id": "A001", "name": "iPhone 15", "category_id": "123"}
        ]}
    ])
    
    params = {
        "start_object": "Category",
        "start_filters": {"name": "手机"},
        "path": ["category"]  # Category → SKU (沿category Link反向)
    }
    
    result = await navigator.navigate(params, ctx)
    
    assert result.success
    assert len(result.data) == 1
    assert result.data[0]["sku_id"] == "A001"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest backend/tests/unit/agent/link/test_navigator.py::test_navigate_single_hop -v`
Expected: FAIL - PathNavigator不存在

- [ ] **Step 3: 实现PathNavigator（单跳）**

```python
# backend/app/services/agent/link/navigator.py
from app.services.agent.link.resolver import LinkResolver
from app.services.agent.tools.registry import ToolContext, ToolResult

class PathNavigator:
    """执行多跳Link导航"""
    
    def __init__(self, resolver: LinkResolver):
        self.resolver = resolver
    
    async def navigate(self, params: dict, ctx: ToolContext) -> ToolResult:
        """沿Link路径导航"""
        try:
            ontology = ctx.ontology_context.get("ontology", {})
            
            # Step 0: 查询起点对象
            current_object = params["start_object"]
            current_rows = await self._query_start(
                current_object,
                params.get("start_filters", {}),
                ctx
            )
            
            if not current_rows:
                return ToolResult(success=True, data=[])
            
            # 逐跳导航
            path = params["path"]
            path_filters = params.get("path_filters", {})
            
            for link_field_slug in path:
                # 解析Link定义
                link_def = self.resolver.resolve_link(
                    current_object, link_field_slug, ontology
                )
                
                if not link_def:
                    return ToolResult(
                        success=False,
                        error=f"'{link_field_slug}' is not a Link field in {current_object}"
                    )
                
                # 执行该跳（反向导航）
                current_rows = await self._navigate_one_hop(
                    current_rows, link_def, ctx
                )
                
                if not current_rows:
                    return ToolResult(success=True, data=[])
                
                # 应用该跳的过滤
                if link_field_slug in path_filters:
                    current_rows = self._apply_filters(
                        current_rows, path_filters[link_field_slug]
                    )
                
                # 更新当前对象类型
                current_object = link_def.target_object
            
            # 应用select和limit
            if params.get("select"):
                current_rows = self._select_fields(current_rows, params["select"])
            
            if params.get("limit"):
                current_rows = current_rows[:params["limit"]]
            
            return ToolResult(success=True, data=current_rows)
        
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
    
    async def _query_start(self, object_name: str, filters: dict, ctx):
        """查询起点对象"""
        filter_list = []
        for key, value in filters.items():
            filter_list.append({
                "field": key,
                "operator": "=",
                "value": value
            })
        
        result = ctx.omaha_service.query_objects(
            object_type=object_name,
            filters=filter_list
        )
        
        return result.get("data", []) if result.get("success") else []
    
    async def _navigate_one_hop(self, current_rows, link_def, ctx):
        """执行单跳导航（反向查询）"""
        pk_values = [
            row.get(link_def.target_key)
            for row in current_rows
            if row.get(link_def.target_key)
        ]
        
        if not pk_values:
            return []
        
        result = ctx.omaha_service.query_objects(
            object_type=link_def.source_object,
            filters=[{
                "field": link_def.foreign_key,
                "operator": "IN",
                "value": pk_values
            }]
        )
        
        return result.get("data", []) if result.get("success") else []
    
    def _apply_filters(self, rows: list[dict], filters: dict) -> list[dict]:
        """应用过滤条件"""
        result = []
        for row in rows:
            match = True
            for key, value in filters.items():
                if key.endswith("_min"):
                    field = key[:-4]
                    if row.get(field, 0) < value:
                        match = False
                        break
                elif key.endswith("_max"):
                    field = key[:-4]
                    if row.get(field, float('inf')) > value:
                        match = False
                        break
                elif row.get(key) != value:
                    match = False
                    break
            
            if match:
                result.append(row)
        
        return result
    
    def _select_fields(self, rows: list[dict], fields: list[str]) -> list[dict]:
        """选择字段"""
        return [
            {k: row.get(k) for k in fields}
            for row in rows
        ]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest backend/tests/unit/agent/link/test_navigator.py::test_navigate_single_hop -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent/link/navigator.py backend/tests/unit/agent/link/test_navigator.py
git commit -m "feat(link): implement PathNavigator for single-hop navigation"
```

---

### Task 11: navigate_path工具注册

**Files:**
- Create: `backend/app/services/agent/tools/builtin/navigate.py`
- Modify: `backend/app/services/agent/tools/registry.py:15-25`
- Modify: `backend/app/services/agent/tools/view.py:115-125`

- [ ] **Step 1: 定义navigate_path工具**

```python
# backend/app/services/agent/tools/builtin/navigate.py
from app.services.agent.providers.base import ToolSpec

NAVIGATE_PATH_SPEC = ToolSpec(
    name="navigate_path",
    description=(
        "Navigate through multiple Link relationships in sequence. "
        "Use this when you need to follow a path like Category → SKU → Review. "
        "Each step can have its own filters."
    ),
    parameters={
        "type": "object",
        "properties": {
            "start_object": {
                "type": "string",
                "description": "Starting object name (e.g., 'Category')"
            },
            "start_filters": {
                "type": "object",
                "description": "Filters for the starting object (e.g., {name: '手机'})",
                "additionalProperties": True
            },
            "path": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Link field slugs to follow (e.g., ['category', 'sku'])"
            },
            "path_filters": {
                "type": "object",
                "description": "Filters for each step (e.g., {sku: {price_min: 1000}})",
                "additionalProperties": True
            },
            "select": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Fields to return from final object"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results"
            }
        },
        "required": ["start_object", "path"],
        "additionalProperties": False
    }
)
```

- [ ] **Step 2: 注册navigate_path到ToolRegistry**

```python
# backend/app/services/agent/tools/registry.py
from app.services.agent.tools.builtin.navigate import NAVIGATE_PATH_SPEC

class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        # 现有工具...
        
        # 新增：navigate_path
        self.register(NAVIGATE_PATH_SPEC, self._execute_navigate_path)
    
    async def _execute_navigate_path(self, params: dict, ctx: ToolContext) -> ToolResult:
        """执行navigate_path（委托给PathNavigator）"""
        from app.services.agent.link import PathNavigator, LinkResolver
        
        resolver = LinkResolver()
        navigator = PathNavigator(resolver)
        
        return await navigator.navigate(params, ctx)
```

- [ ] **Step 3: 集成到ToolRegistryView**

```python
# backend/app/services/agent/tools/view.py
class ToolRegistryView:
    
    async def execute(self, name: str, params: dict, ctx: ToolContext) -> ToolResult:
        if name == "navigate_path":
            # 委托给PathNavigator
            from app.services.agent.link import PathNavigator
            navigator = PathNavigator(self.link_resolver)
            return await navigator.navigate(params, ctx)
        elif name == "refine_objectset":
            return await self._execute_refine(params, ctx)
        # ... 其余逻辑
```

- [ ] **Step 4: 写测试**

```python
# backend/tests/unit/agent/test_view.py
@pytest.mark.asyncio
async def test_navigate_path_tool():
    ontology = {
        "objects": [
            {"name": "Category", "slug": "category", "properties": [...]},
            {"name": "SKU", "slug": "sku", "properties": [
                {"name": "类目", "slug": "category", "type": "link", "link": {...}}
            ]}
        ]
    }
    
    omaha_service = MagicMock()
    omaha_service.query_objects = AsyncMock(side_effect=[
        {"success": True, "data": [{"category_id": "123"}]},
        {"success": True, "data": [{"sku_id": "A001"}]}
    ])
    
    view = ToolRegistryView(builtin=MagicMock(), derived=[])
    ctx = ToolContext(omaha_service=omaha_service, ontology_context={"ontology": ontology})
    
    result = await view.execute("navigate_path", {
        "start_object": "Category",
        "start_filters": {"name": "手机"},
        "path": ["category"]
    }, ctx)
    
    assert result.success
    assert len(result.data) == 1
```

Run: `pytest backend/tests/unit/agent/test_view.py::test_navigate_path_tool -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent/tools/builtin/navigate.py backend/app/services/agent/tools/registry.py backend/app/services/agent/tools/view.py backend/tests/unit/agent/test_view.py
git commit -m "feat(link): register navigate_path tool for multi-hop navigation"
```

---

### Task 12: 多跳导航测试

**Files:**
- Test: `backend/tests/unit/agent/link/test_navigator.py`

- [ ] **Step 1: 写测试 - 多跳导航**

```python
# backend/tests/unit/agent/link/test_navigator.py
@pytest.mark.asyncio
async def test_navigate_multi_hop():
    ontology = {
        "objects": [
            {"name": "Category", "slug": "category", "properties": [{"name": "ID", "slug": "id", "type": "string"}]},
            {
                "name": "SKU",
                "slug": "sku",
                "properties": [
                    {"name": "ID", "slug": "id", "type": "string"},
                    {"name": "类目", "slug": "category", "type": "link", "link": {"target": "Category", "foreign_key": "category_id", "target_key": "id"}}
                ]
            },
            {
                "name": "Review",
                "slug": "review",
                "properties": [
                    {"name": "评分", "slug": "rating", "type": "integer"},
                    {"name": "商品", "slug": "sku", "type": "link", "link": {"target": "SKU", "foreign_key": "sku_id", "target_key": "id"}}
                ]
            }
        ]
    }
    
    resolver = LinkResolver()
    navigator = PathNavigator(resolver)
    
    ctx = MagicMock()
    ctx.ontology_context = {"ontology": ontology}
    ctx.omaha_service.query_objects = AsyncMock(side_effect=[
        # 第1次：查询Category
        {"success": True, "data": [{"id": "123", "name": "手机"}]},
        # 第2次：Category → SKU
        {"success": True, "data": [{"id": "A001", "category_id": "123"}]},
        # 第3次：SKU → Review
        {"success": True, "data": [
            {"review_id": "R1", "sku_id": "A001", "rating": 5},
            {"review_id": "R2", "sku_id": "A001", "rating": 3}
        ]}
    ])
    
    params = {
        "start_object": "Category",
        "start_filters": {"name": "手机"},
        "path": ["category", "sku"],  # Category → SKU → Review
        "path_filters": {
            "sku": {"rating_min": 4}  # 只要评分>=4的评论
        }
    }
    
    result = await navigator.navigate(params, ctx)
    
    assert result.success
    assert len(result.data) == 1  # 只有R1（rating=5）
    assert result.data[0]["rating"] == 5
```

- [ ] **Step 2: 运行测试确认通过**

Run: `pytest backend/tests/unit/agent/link/test_navigator.py::test_navigate_multi_hop -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/agent/link/test_navigator.py
git commit -m "test(link): add multi-hop navigation test"
```

---

### Task 13: E2E测试 - 多跳导航

**Files:**
- Test: `backend/tests/e2e/test_link_scenarios.py`

- [ ] **Step 1: 添加多跳场景测试**

```python
# backend/tests/e2e/test_link_scenarios.py
@pytest.mark.asyncio
async def test_multi_hop_navigation_scenario(db_session, tenant, ecommerce_ontology):
    """
    场景：用户问"手机类目下评分>4的商品有哪些？"
    预期：LLM调用 navigate_path 工具
    """
    chat_service = ChatService(db_session)
    
    session = chat_service.create_session(
        tenant_id=tenant.id,
        ontology_id=ecommerce_ontology.id
    )
    
    response = await chat_service.send_message(
        session_id=session.id,
        user_message="手机类目下评分大于4分的商品有哪些？"
    )
    
    assert response["success"]
    
    # 验证工具调用
    tool_calls = response.get("tool_calls", [])
    assert any("navigate_path" in call["name"] for call in tool_calls)
```

- [ ] **Step 2: 运行E2E测试**

Run: `pytest backend/tests/e2e/test_link_scenarios.py::test_multi_hop_navigation_scenario -v -s`
Expected: PASS（如果LLM可用）

- [ ] **Step 3: Commit**

```bash
git add backend/tests/e2e/test_link_scenarios.py
git commit -m "test(link): add E2E test for multi-hop navigation scenario"
```

---

### Task 14: 更新文档

**Files:**
- Modify: `backend/CLAUDE.md`
- Create: `docs/link-type-guide.md`

- [ ] **Step 1: 更新CLAUDE.md**

```markdown
# backend/CLAUDE.md

## Link类型系统

**Link是本体中的一等公民，用于定义对象间的关系。**

### YAML配置格式

```yaml
objects:
  - name: SKU
    properties:
      - name: 类目
        slug: category
        type: link
        target: Category              # 目标对象名称
        foreign_key: category_id      # 源表外键字段
        target_key: category_id       # 目标表主键（可选，默认"id"）
```

### 自动生成的工具

**1. 自动展开Link字段**
- 查询结果中，Link字段自动变成完整对象
- 例如：`search_sku()` 返回的 `category` 字段是完整的Category对象

**2. 反向导航工具**
- 自动生成 `get_{target}_{source}s` 工具
- 例如：`get_category_skus(category_id)` 返回该类目的所有SKU

**3. 多跳导航工具**
- `navigate_path` 工具支持链式查询
- 例如：Category → SKU → Review → Customer

### 测试

```bash
# 单元测试
pytest backend/tests/unit/agent/link/ -v

# E2E测试
pytest backend/tests/e2e/test_link_scenarios.py -v
```
```

- [ ] **Step 2: 创建Link类型使用指南**

```markdown
# docs/link-type-guide.md

# Link类型使用指南

## 什么是Link？

Link是本体中定义对象间关系的方式，类似数据库的外键，但支持跨数据源。

## 定义Link

```yaml
objects:
  - name: SKU
    slug: sku
    datasource: mysql_product
    properties:
      - name: 类目
        slug: category
        type: link
        target: Category
        foreign_key: category_id
        target_key: category_id  # 可选，默认"id"
```

## 使用Link

### 1. 自动展开

查询SKU时，category字段自动展开：

```python
search_sku(name="iPhone 15")
# 返回：
{
  "sku_id": "A001",
  "category": {
    "category_id": "123",
    "name": "手机"
  }
}
```

### 2. 反向导航

从Category查所有SKU：

```python
get_category_skus(category_id="123")
# 返回该类目下的所有SKU
```

### 3. 多跳导航

一次调用完成多跳查询：

```python
navigate_path({
  "start_object": "Category",
  "start_filters": {"name": "手机"},
  "path": ["category", "sku", "review"],
  "path_filters": {
    "review": {"rating_min": 4}
  }
})
# 返回：手机类目下评分>4的所有评论
```

## 跨数据源Link

Link支持跨数据源：

```yaml
# SKU在MySQL
- name: SKU
  datasource: mysql_product

# Review在MongoDB
- name: Review
  datasource: mongo_review
  properties:
    - name: 商品
      type: link
      target: SKU  # 跨源Link
      foreign_key: sku_id
```

## 限制

- 不支持多对多关系（需要中间表）
- 大数据集（>1000行）可能较慢
- 建议添加数据库索引优化性能
```

- [ ] **Step 3: Commit**

```bash
git add backend/CLAUDE.md docs/link-type-guide.md
git commit -m "docs: add Link type system documentation and usage guide"
```

---

### Task 15: 最终测试

**Files:**
- All test files

- [ ] **Step 1: 运行所有单元测试**

Run: `cd backend && pytest tests/unit/ -v`
Expected: 所有测试通过

- [ ] **Step 2: 运行所有集成测试**

Run: `cd backend && pytest tests/integration/ -v`
Expected: 所有测试通过

- [ ] **Step 3: 运行E2E测试**

Run: `cd backend && pytest tests/e2e/test_link_scenarios.py -v -s`
Expected: 测试通过或SKIP（如果无LLM）

- [ ] **Step 4: 检查测试覆盖率**

Run: `cd backend && pytest tests/unit/agent/link/ --cov=app/services/agent/link --cov-report=term-missing`
Expected: 覆盖率 > 80%

- [ ] **Step 5: 最终commit**

```bash
git add -A
git commit -m "feat(link): complete Link type system implementation

Implemented Palantir Foundry-style Link system:
- Link as first-class property type in ontology
- Auto-expansion of Link fields in query results
- Reverse navigation tool generation (get_{target}_{source}s)
- Multi-hop path navigation (navigate_path)
- Cross-datasource support (MySQL/MongoDB/Excel)

Test coverage:
- Unit tests: LinkResolver, LinkExpander, PathNavigator
- Integration tests: End-to-end Link scenarios
- E2E tests: Real LLM usage scenarios

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## 实施完成

**交付物：**
- ✅ Link类型数据模型（数据库 + ORM）
- ✅ Link引擎（Resolver + Expander + Navigator）
- ✅ 自动展开Link字段
- ✅ 反向导航工具生成
- ✅ 多跳导航工具（navigate_path）
- ✅ 完整测试覆盖（单元 + 集成 + E2E）
- ✅ 文档（CLAUDE.md + 使用指南）

**下一步：**
使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 执行此计划。

