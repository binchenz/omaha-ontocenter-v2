# Per-ObjectType Query Tools + ObjectSet API (Stage 1)

**Goal:** 用每个 ObjectType 自动派生的扁平参数工具，替代当前的泛型 `query_data(filters)`。字段名、operator、值类型从本体推导，OpenAI strict mode 完全兼容；同时为后续 Stage 2-5 立起 ObjectSet 中央总线。

**灵感来源:** Palantir Foundry — 每个 ObjectType 编译成 ObjectSet API + 一个类型化的 search 工具。

---

## 1. 现状与问题

当前 `query_data(object_type, filters: [{field, operator, value}], limit)`：

- 嵌套 array+object schema 触发 OpenAI strict mode 边界（已绕过，但是补丁）
- filter 值无类型，LLM 自行猜 `city` 是字符串、`price` 是数字
- 无字段名校验，拼错字段静默返回空
- LLM 不知道哪些字段、operator 合法

JSON-string 兜底虽 work，但**违背本体论**：filter 应是一等公民，不是自由文本。

## 2. 设计

### 2.1 ObjectSet 抽象（保留，作为长期中央总线）

```python
@dataclass(frozen=True)
class Filter:
    field: str
    operator: str          # eq/ne/gt/gte/lt/lte/in/contains
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

    def where(self, **conditions) -> ObjectSet
    def select(self, *fields) -> ObjectSet
    def order_by(self, field: str, desc: bool = False) -> ObjectSet
    def limit_to(self, n: int) -> ObjectSet
    def execute(self, omaha: OmahaService) -> list[dict]
```

不可变、链式、惰性。OmahaService 留作 backend，零改动。

**Stage 1 范围克制**：不实现 `pivot_to`（Stage 3）、`group_by`（Stage 4）、RID 注册（Stage 4）、缓存（按需）。但接口契约从 Stage 1 立起来，后续 Stage 叠加而非重写。

### 2.2 Per-Object 工具生成器

`ObjectTypeToolFactory.build(ontology) -> list[ToolSpec]`，每个 ObjectType 派生 2 个工具：

**`search_<slug>`** — 扁平参数：
- 每个可过滤 property 一个参数：`<field>` (eq) 或 `<field>_min/_max/_contains`（按类型派生）
- `sort_by`: 可排序字段的 enum，附 `_asc`/`_desc` 后缀
- `select`: 字段名 enum 数组
- `limit`: 整数（默认 100）

**`count_<slug>`** — 同 filter，返回行数。

例（slug=`product`，业务名 `商品`）：
```
search_product(
  sku?: string,
  name_contains?: string,
  city?: string,             # Stage 1 一律 string，不下发 enum 值域
  price_min?: number,
  price_max?: number,
  sort_by?: enum["sku","price","price_desc",...],
  select?: array<enum["sku","name","city","price"]>,
  limit?: integer
)
```

LLM 永不见嵌套 filter 数组。字段名来自本体。工具 description 里附原中文名 + 业务上下文，LLM 选工具时能理解。

### 2.3 ObjectType slug（DB schema 改动）

OpenAI 工具名规则：`^[a-zA-Z0-9_-]{1,64}$`。中文名（如 `商品`、`订单明细`）会被拒。

**改动**：`OntologyObject` 表增加 `slug` 列（unique within tenant）。
- 建模时 `OntologyImporter` 自动生成 slug：英文名 lowercase；中文名/含特殊字符 → 拼音或 `obj_<hash>`
- `confirm_ontology` / `edit_ontology` 维护 slug 一致性
- factory 用 slug 命名工具
- 字段同理：property 增加 slug 列（少见但要防）

Alembic migration：`add_slug_to_ontology_object_and_property.py`。

### 2.4 ToolRegistryView（多租户隔离）

`global_registry` 是进程单例，per-Object 工具是项目维度 → 不能直接写进 global_registry，否则项目间串台。

```python
class ToolRegistryView:
    def __init__(self, builtin: ToolRegistry, derived: list[ToolSpec]):
        self._builtin = builtin
        self._derived = {spec.name: spec for spec in derived}
    
    def get_specs(self, whitelist: list[str] | None = None) -> list[ToolSpec]: ...
    def execute(self, name: str, params: dict, ctx: ToolContext) -> ToolResult: ...
```

- `builtin` = global_registry（list_objects, get_schema, scan_tables, infer_ontology, …）
- `derived` = factory 本轮产出的 search/count 工具
- `ExecutorAgent` 用 view 替代直接读 global_registry

### 2.5 每轮重新派生工具（不缓存）

自然语言建模会在 session 内频繁改 ontology（confirm/edit/rename/add-property）。**派生工具必须随 ontology 即时刷新**，否则 "刚改完字段就查询" 会用旧 schema。

**实现**：`ChatServiceV2.send_message` 每轮调 `factory.build(latest_ontology)` 构造新 view，喂给 ExecutorAgent。Python 字典操作毫秒级，不缓存。

### 2.6 Skill whitelist 通配符

`data_query.yaml` 当前写死工具名。派生工具是动态的，需通配符：

```yaml
allowed_tools:
  - list_objects
  - get_schema
  - get_relationships
  - search_*       # 通配，匹配所有派生 search 工具
  - count_*
  - generate_chart
  - auto_chart
  - query_data     # 兜底，本 release 保留
```

`SkillLoader` + `ToolRegistryView.get_specs(whitelist)` 支持前缀匹配（`*` 结尾）。

### 2.7 ExecutorAgent 首轮 `tool_choice` 改 `auto`

`@/Users/wangfushuaiqi/omaha_ontocenter/backend/app/services/agent/orchestrator/executor.py:78` 当前首轮强制 `required`。问题：
- 闲聊"你好"也强制调工具，体验差
- 大工具集（10 对象 × 2 = 20+ 派生工具 + 18 内置）下选错率上升
- deepseek-reasoner 已不支持 tool_choice，需特例

**改动**：首轮统一 `auto`，删除 `required` 分支。

## 3. 文件结构

- `app/services/agent/objectset/__init__.py` — ObjectSet, Filter, Sort
- `app/services/agent/objectset/compiler.py` — ObjectSet → OmahaService 调用
- `app/services/agent/tools/factory.py` — ObjectTypeToolFactory
- `app/services/agent/tools/view.py` — ToolRegistryView
- `app/models/ontology/object.py` — 加 `slug` 列
- `app/services/ontology/slug.py` — slug 生成（英文 lower / 中文拼音 / 兜底 hash）
- `app/services/ontology/importer.py` — confirm/edit 时维护 slug
- `app/services/agent/chat_service.py` — 每轮 build view
- `app/services/agent/orchestrator/executor.py` — 用 view，删 required
- `app/services/agent/skills/loader.py` + `executor.py` — whitelist 通配符
- `app/services/agent/skills/definitions/data_query.yaml` — 加 `search_*` / `count_*`
- `alembic/versions/<ts>_add_slug_to_ontology.py`
- `tests/unit/agent/test_factory.py` / `test_view.py` / `test_objectset.py` / `test_slug.py`

不动 OmahaService。

## 4. 范围外（后续阶段）

- Value Type Registry（枚举值域、货币格式化、`深圳`/`shenzhen` 归一化）— Stage 2
- Link 遍历（`pivot_to`）— Stage 3
- 聚合工具（`aggregate_<slug>`、`group_by`）— Stage 4
- ObjectSet RID 状态机（多轮"刚才的查询再加条件"）— Stage 4
- Action Type — Stage 5

## 5. 验收标准

1. Project 10（含 Product）每轮 chat 时 view 含 `search_product` 与 `count_product`
2. 工具 schema 通过 OpenAI strict 校验（无嵌套 array+object）
3. **E2E filtered-query-cn**: "深圳的商品" → LLM 调 `search_product(city="深圳")` → 至少能传值（值匹配率不强求，留给 Stage 2）
4. **E2E filtered-multi**: "深圳且价格>20" → 调 `search_product(city="深圳", price_min=20)`
5. **E2E unknown-field**: bogus 字段在 OpenAI 侧 schema 拒掉
6. **E2E modeling-then-query**: 同 session 内 `confirm_ontology` 后立即查询，工具列表已含新对象
7. **E2E rename-then-query**: `edit_ontology` 改字段名后下一轮查询的工具参数用新名
8. **E2E chinese-object-name**: 用户建模出名为"商品"的对象，工具叫 `search_product`（slug），可正常调用
9. **E2E multi-project**: 项目 A 和 B 各自的派生工具不串台
10. **E2E greeting**: "你好" → 不强制调工具，自然回复
11. 当前 21/25 通过场景不退化
12. 旧 `query_data` 仍 work（兜底）

## 6. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 工具数量上 50+ 后 LLM 选择困难 | 工具描述加业务上下文；skill prompt 注入"按对象名匹配" |
| slug 冲突（两个对象都映射到同 slug） | importer 在生成时检查同租户唯一性，冲突附 `_2` 后缀 |
| 每轮重新派生在百对象项目下慢 | 派生纯字典操作，<1ms；如真成瓶颈再加 ontology version + cache |
| edit_ontology 中途 schema 改名导致 LLM 工具调用参数失效 | 改名是一轮内完成，下一轮 view 已是新 schema；当轮调用失败 LLM 自然重试 |
