# Link类型系统设计文档

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现Palantir Foundry风格的Link类型系统，支持跨数据源关系定义、自动JOIN展开、反向导航和链式导航

**Architecture:** 四层架构 - Tool Layer（动态工具生成）→ Link Engine（Link解析/展开/导航）→ Data Access Layer（统一数据源接口）→ Data Sources（MySQL/MongoDB/Excel/PostgreSQL）

**Tech Stack:** Python 3.11, SQLAlchemy, FastAPI, 现有OmahaService/Connector架构

---

## 1. 背景与目标

### 1.1 当前问题

**问题1：关系未被利用**
- 本体定义了relationships表，但查询时不使用
- 用户问"手机类目下有哪些商品？"需要两步：
  1. 查Category得到category_id
  2. 查SKU where category_id=xxx
- LLM容易忘记中间步骤，产生幻觉

**问题2：跨对象查询复杂**
- 多跳查询（Category → SKU → Review → Customer）需要LLM自己拆解
- 参数传递容易出错
- 无法利用关系优化查询

**问题3：无反向导航**
- 只能正向查询（SKU → Category）
- 无法反向查询（Category → 所有SKU）
- 需要手动构造过滤条件

### 1.2 设计目标

**核心目标：**
1. Link是一等公民 - 在本体层定义，工具层自动支持
2. 自动展开 - 查询结果中Link字段自动变成完整对象
3. 反向导航 - 自动生成反向查询工具
4. 链式导航 - 一次调用完成多跳查询
5. 跨数据源 - 支持MySQL/MongoDB/Excel之间的Link

**非目标（Stage 2不做）：**
- ❌ 查询优化（缓存、批量查询）
- ❌ 物化视图
- ❌ 数据仓库集成
- ❌ Link完整性验证

---

## 2. 架构设计

### 2.1 系统分层

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Tool Layer (工具层)                            │
│  ─────────────────────────────────────────────────────  │
│  • search_sku / count_sku / aggregate_sku              │
│  • get_category_skus (反向导航，自动生成)               │
│  • navigate_path (多跳导航)                             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Link Engine (Link引擎)                        │
│  ─────────────────────────────────────────────────────  │
│  • LinkResolver: 解析Link定义                            │
│  • LinkExpander: 展开Link字段（单跳）                   │
│  • PathNavigator: 执行多跳导航                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Data Access Layer (数据访问层)                │
│  ─────────────────────────────────────────────────────  │
│  • OmahaService: 执行SQL查询                             │
│  • MongoConnector: 执行MongoDB查询                       │
│  • ExcelConnector: 读取Excel                             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Data Sources (数据源)                         │
│  MySQL    MongoDB    Excel    PostgreSQL               │
└─────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

**LinkResolver（Link解析器）**
- 输入：对象名 + Link字段slug + 本体定义
- 输出：LinkDefinition（包含源/目标对象、外键、数据源信息）
- 职责：从本体中解析Link关系

**LinkExpander（Link展开器）**
- 输入：查询结果 + 对象定义
- 输出：展开后的结果（Link字段变成完整对象）
- 职责：自动展开所有Link字段（极简版：逐行查询，无优化）

**PathNavigator（路径导航器）**
- 输入：起点对象 + Link路径 + 过滤条件
- 输出：终点对象列表
- 职责：执行多跳Link导航

---

## 3. 数据模型

### 3.1 数据库Schema扩展

```python
class ObjectProperty(Base):
    __tablename__ = "object_properties"
    
    id = Column(Integer, primary_key=True)
    object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    data_type = Column(String, nullable=False)  # "string", "number", "link"
    semantic_type = Column(String)
    description = Column(Text)
    
    # Link类型专用字段
    link_target_id = Column(Integer, ForeignKey("ontology_objects.id"))
    link_foreign_key = Column(String)      # 源表的外键字段名
    link_target_key = Column(String, default="id")  # 目标表的主键字段名
    
    link_target = relationship("OntologyObject", foreign_keys=[link_target_id])
```

**设计决策：**
- Link是属性的一种类型（和string/number平级）
- link_target_key默认"id"，覆盖90%场景
- 支持自引用Link（Category.parent → Category）

### 3.2 YAML配置格式

```yaml
objects:
  - name: SKU
    slug: sku
    datasource: mysql_product
    source_entity: sku
    properties:
      - name: 类目
        slug: category
        type: link
        target: Category              # 目标对象名称
        foreign_key: category_id      # 源表外键字段
        target_key: category_id       # 目标表主键（可选，默认"id"）
        description: 商品所属类目

  - name: Category
    slug: category
    properties:
      - name: 类目ID
        slug: category_id
        type: string
      - name: 父类目
        slug: parent
        type: link
        target: Category              # 自引用Link
        foreign_key: parent_id
        target_key: category_id
```

### 3.3 本体导入（两阶段）

**阶段1：创建对象 + 非Link属性**
```python
for obj_def in ontology["objects"]:
    obj = store.create_object(...)
    for prop in obj_def["properties"]:
        if prop["type"] != "link":
            store.add_property(...)
```

**阶段2：添加Link属性**
```python
for obj_def in ontology["objects"]:
    for prop in obj_def["properties"]:
        if prop["type"] == "link":
            store.add_property(
                data_type="link",
                link_target=prop["target"],
                link_foreign_key=prop["foreign_key"],
                link_target_key=prop.get("target_key", "id")
            )
```

**为什么两阶段？** 解决自引用Link的循环依赖问题

---

## 4. 功能设计

### 4.1 自动展开Link字段

**用户体验：**
```python
# 用户调用
search_sku(name="iPhone 15")

# 返回结果（category字段自动展开）
{
  "data": [{
    "sku_id": "A001",
    "name": "iPhone 15",
    "price": 5999,
    "category": {              # ← 自动展开
      "category_id": "123",
      "name": "手机",
      "parent": {              # ← 递归展开
        "category_id": "1",
        "name": "数码产品"
      }
    }
  }]
}
```

**实现逻辑：**
1. 查询完成后，识别所有Link字段
2. 逐个Link字段，逐行查询目标对象
3. 将目标对象填充到Link字段

**极简版特点：**
- 无缓存
- 无批量查询优化
- 逐行查询（可能有N+1问题，但先让它work）

### 4.2 反向导航工具

**自动生成规则：**
```
SKU.category → Category
生成工具：get_category_skus(category_id) → 返回该类目的所有SKU
```

**工具命名：** `get_{target_slug}_{source_slug}s`

**用户体验：**
```python
# LLM调用
get_category_skus(category_id="123", limit=10)

# 返回
{
  "data": [
    {"sku_id": "A001", "name": "iPhone 15", ...},
    {"sku_id": "A002", "name": "iPhone 14", ...}
  ]
}
```

### 4.3 多跳导航

**工具定义：**
```python
navigate_path({
    "start_object": "Category",
    "start_filters": {"name": "手机"},
    "path": ["category", "sku", "review"],  # Link字段路径
    "path_filters": {
        "review": {"rating_min": 4}
    },
    "select": ["review_id", "content", "rating"],
    "limit": 100
})
```

**执行流程：**
1. 查询起点：Category where name='手机'
2. 第1跳：沿category Link → SKU（反向查询）
3. 第2跳：沿sku Link → Review（反向查询）
4. 应用过滤：rating >= 4
5. 返回结果

**关键设计：**
- path指定Link字段名（不是对象名）
- 每跳可以应用过滤（减少中间结果集）
- 提前终止（某跳无结果则停止）

---

## 5. 实现细节

### 5.1 LinkDefinition数据结构

```python
@dataclass
class LinkDefinition:
    source_object: str          # "SKU"
    source_slug: str            # "sku"
    link_field: str             # "category"
    target_object: str          # "Category"
    target_slug: str            # "category"
    foreign_key: str            # "category_id"
    target_key: str             # "category_id" 或 "id"
    datasource_type: str        # "mysql"
    datasource_id: str          # "mysql_product"
```

### 5.2 跨数据源JOIN策略

**应用层JOIN（极简版）：**
1. 先查源表（如MySQL的SKU）
2. 收集外键值
3. 再查目标表（如MongoDB的Review）
4. 在Python内存中合并

**特点：**
- 简单直接
- 支持任意数据源组合
- 性能可能不佳（N+1问题）

**未来优化方向：**
- 批量查询（一次查多个ID）
- 对象级缓存（同一对象只查一次）
- 物化视图（预计算常用JOIN）

### 5.3 反向导航的逻辑

**正向Link：** SKU.category → Category
- SKU表有 category_id 字段
- 查询：SELECT * FROM category WHERE category_id = ?

**反向导航：** Category → SKU
- 查询：SELECT * FROM sku WHERE category_id = ?
- 即：查询引用该Category的所有SKU

**实现：**
```python
# 从LinkDefinition反向推导
# link_def: SKU.category → Category
# 反向查询：查询 source_object where foreign_key = target_id

result = omaha_service.query_objects(
    object_type=link_def.source_object,  # SKU
    filters=[{
        "field": link_def.foreign_key,    # category_id
        "operator": "=",
        "value": target_id
    }]
)
```

---

## 6. 测试计划

### 6.1 单元测试

**test_link_resolver.py**
- 解析Link定义
- 处理自引用Link
- 处理不存在的Link

**test_link_expander.py**
- 展开单个Link字段
- 展开多个Link字段
- 递归展开（Link的Link）
- 跨数据源展开

**test_path_navigator.py**
- 单跳导航
- 多跳导航
- 逐跳过滤
- 提前终止

### 6.2 集成测试

**test_link_e2e.py**
- 场景1：电商多数据源（MySQL + MongoDB + Excel）
- 场景2：自引用Link（Category树）
- 场景3：链式导航（Category → SKU → Review → Customer）

### 6.3 E2E测试

**test_chat_scenarios_link.py**
- 用户问："手机类目下有哪些商品？"
- 用户问："手机类目下评分>4的商品有哪些？"
- 用户问："手机类目下评分最高的商品的用户画像分布？"

---

## 7. 实施计划

### Week 1: Link基础（5天）

**Day 1-2: 数据模型**
- 数据库migration（添加link_*字段）
- OntologyStore扩展（add_property支持Link）
- OntologyImporter两阶段导入

**Day 3-4: Link引擎核心**
- LinkResolver实现
- LinkExpander实现（极简版）
- 集成到ToolRegistryView

**Day 5: 测试**
- 单元测试（resolver + expander）
- 集成测试（单跳Link）

### Week 2: 反向导航（5天）

**Day 1-2: 工具生成**
- ObjectTypeToolFactory生成反向导航工具
- 工具命名规则

**Day 3-4: 执行逻辑**
- ToolRegistryView._execute_reverse_nav
- 反向查询逻辑

**Day 5: 测试**
- 单元测试（反向导航）
- E2E测试（用户场景）

### Week 3: 多跳导航（5天）

**Day 1-2: PathNavigator实现**
- navigate_path工具定义
- 逐跳执行逻辑
- 过滤应用

**Day 3-4: 集成测试**
- 多跳场景测试
- 跨数据源测试

**Day 5: E2E测试 + 文档**
- 完整用户场景测试
- 更新CLAUDE.md
- 更新本体YAML格式文档

---

## 8. 风险与限制

### 8.1 已知限制

**性能限制：**
- 极简版有N+1查询问题
- 大数据集（>1000行）可能很慢
- 建议：添加过滤条件或创建索引

**功能限制：**
- 不支持多对多关系（需要中间表）
- 不支持Link完整性验证
- 不支持Link的权限控制

### 8.2 未来优化方向

**性能优化（Stage 3）：**
- 批量查询（减少网络往返）
- 对象级缓存（LRU）
- 查询计划优化（智能选择策略）

**功能增强（Stage 4）：**
- 物化视图（预计算常用JOIN）
- 数据仓库集成（DuckDB/ClickHouse）
- Link完整性验证

---

## 9. 成功标准

**功能完整性：**
- ✅ 支持Link类型定义（YAML + 数据库）
- ✅ 自动展开Link字段
- ✅ 反向导航工具自动生成
- ✅ 多跳导航（navigate_path）
- ✅ 跨数据源Link（MySQL/MongoDB/Excel）

**测试覆盖：**
- ✅ 单元测试覆盖率 > 80%
- ✅ 集成测试覆盖核心场景
- ✅ E2E测试通过（真实LLM调用）

**用户体验：**
- ✅ LLM能正确使用反向导航工具
- ✅ LLM能正确使用navigate_path
- ✅ 查询结果符合预期（Link字段已展开）

**性能基准：**
- ✅ 单跳Link展开 < 1秒（100行）
- ✅ 多跳导航 < 3秒（3跳，每跳100行）
- ⚠️  超过1000行时给出明确提示

---

## 10. 参考资料

**Palantir Foundry文档：**
- Ontology概念：https://www.palantir.com/docs/foundry/ontology/
- Link类型：https://www.palantir.com/docs/foundry/ontology/object-types/

**内部文档：**
- 当前本体系统：`backend/app/services/ontology/`
- 工具生成逻辑：`backend/app/services/agent/tools/factory.py`
- 查询执行：`backend/app/services/legacy/financial/omaha.py`
