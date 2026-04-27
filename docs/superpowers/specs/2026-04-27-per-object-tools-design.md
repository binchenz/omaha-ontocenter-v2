# Per-ObjectType Query Tools + ObjectSet API (Stage 1)

**Goal:** 用每个 ObjectType 自动派生的扁平参数工具，替代当前的泛型 `query_data(filters)`。字段名、operator、值类型从本体推导，OpenAI strict mode 完全兼容。

**灵感来源:** Palantir Foundry — 每个 ObjectType 编译成 ObjectSet API + 一个类型化的 search 工具。

---

## 1. 现状与问题

当前 `query_data(object_type, filters: [{field, operator, value}], limit)` 的问题：

- 嵌套 array+object schema 触发 OpenAI strict mode 边界（已绕过，但是个补丁）
- filter 值是无类型 JSON，LLM 必须自己知道 `city` 是字符串、`price` 是数字
- 没有字段名校验 —— 拼错字段静默返回空
- LLM 不知道哪些字段、哪些 operator 合法

JSON-string 兜底（`filters_json`）虽然 work，但**违背本体论**：filter 应是带类型的一等公民，不是自由文本。

## 2. 设计

### 2.1 ObjectSet 抽象（OmahaService 之上的新层）

```python
class ObjectSet:
    object_type: str
    filters: list[Filter]      # typed, immutable
    selected: list[str] | None
    sort: list[Sort]
    limit: int | None

    def where(self, **conditions) -> ObjectSet     # returns new ObjectSet
    def select(self, *fields) -> ObjectSet
    def order_by(self, field, desc=False) -> ObjectSet
    def limit_to(self, n) -> ObjectSet
    def execute(self, omaha_service) -> list[dict] # compiles to SQL
```

不可变、链式、惰性（`.execute()` 才出 SQL）。OmahaService 保留为 backend。

### 2.2 Per-Object 工具生成器

`ObjectTypeToolFactory.build_tools(ontology) -> list[ToolSpec]`

每个已确认的 ObjectType 派生 2 个工具：

**`search_<ObjectName>`** — 扁平参数：
- 每个可过滤 property 一个参数：`<field>` (eq) 或 `<field>_min/_max/_contains`（按类型派生）
- `sort_by`: 该对象可排序字段的 enum，附带 `_asc`/`_desc` 后缀
- `select`: 字段名 enum 数组
- `limit`: 整数（默认 100）

例：`Product(sku, name, city, price)` 派生：
```
search_Product(
  sku?: string,
  name?: string,
  name_contains?: string,
  city?: enum["北京","上海","深圳",...],
  price_min?: number,
  price_max?: number,
  sort_by?: enum["sku","name","price","price_desc",...],
  select?: array<enum["sku","name","city","price"]>,
  limit?: integer
)
```

**`count_<ObjectName>`** — 同 filter 参数，返回行数。

LLM 永远看不到嵌套 filter 数组。字段名/枚举值都来自本体。

### 2.3 Skill 提示词

`query.yaml` 不再讲 `query_data`。运行时从 registry 拉取所有 `search_*`/`count_*` 工具列表注入提示词，加一句 "每个对象有自己的 search 工具，按用户问题挑对应的"。

### 2.4 兼容

`query_data` 保留一个 release 作为后备（skill 提示词不再提它）。Stage 2 后移除。

## 3. 文件结构

- `app/services/agent/objectset/__init__.py` — ObjectSet, Filter, Sort
- `app/services/agent/objectset/compiler.py` — ObjectSet → OmahaService 调用
- `app/services/agent/tools/factory.py` — ObjectTypeToolFactory
- `tests/unit/agent/test_factory.py` — 单测
- `app/services/agent/chat_service.py` — 每个 session 启动时把派生工具注册进 runtime
- `app/services/agent/skills/definitions/query.yaml` — 提示词更新

不动 OmahaService、本体模型、DB schema。

## 4. 范围外（后续阶段）

- 聚合工具 (`aggregate_<Object>`) — Stage 4
- Link 遍历 (`linked_orders_filter`) — Stage 3
- ObjectSet RID 状态机 — Stage 4
- Value Type 注册表（枚举值域、货币格式化）— Stage 2；本阶段 enum 字段先回退到 string

## 5. 验收标准

1. Project 10 (含 Product) 启动后 registry 含 `search_Product` 与 `count_Product`
2. 工具 schema 通过 OpenAI strict 校验（无嵌套 array+object）
3. E2E `filtered-query-cn`: "深圳的商品" → LLM 调 `search_Product(city="深圳")` → 仅深圳行
4. E2E `filtered-multi`: "深圳且价格>20" → LLM 调 `search_Product(city="深圳", price_min=20)`
5. E2E `unknown-field`: bogus 字段在 OpenAI 侧就被 schema 拒掉
6. 当前 21/25 通过场景不退化
7. 旧 `query_data` 仍 work（向后兼容）
