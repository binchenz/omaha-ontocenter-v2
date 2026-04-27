# Per-ObjectType Query Tools + ObjectSet API

**Goal:** Replace the generic `query_data(object_type, filters)` tool with per-ObjectType auto-generated tools whose schemas are derived from the ontology. Eliminates filter pass-through bugs, enables field-name validation at the LLM-schema layer, and lays the groundwork for ObjectSet composition.

**Inspired by:** Palantir Foundry — every ObjectType compiles into an ObjectSet API + a typed search tool.

---

## Problem

The current `query_data` tool is generic: `(object_type, filters: [{field, operator, value}], limit)`. This forces:

- Nested array+object schemas that OpenAI strict mode rejects.
- Filter values as untyped JSON (LLM has to know city is a string, price is a number).
- No field-name validation — typos surface as silent empty results.
- LLM has no idea what fields/operators are valid until it tries.

The JSON-string workaround (`filters_json`) works but violates the ontology principle: filters should be first-class typed concepts, not free text.

---

## Design

### 1. ObjectSet abstraction (new layer above OmahaService)

```python
class ObjectSet:
    object_type: str
    filters: list[Filter]      # typed, immutable
    selected: list[str] | None
    sort: list[Sort]
    limit: int | None

    def where(self, **conditions) -> ObjectSet  # returns new ObjectSet
    def select(self, *fields) -> ObjectSet
    def order_by(self, field, desc=False) -> ObjectSet
    def limit_to(self, n) -> ObjectSet
    def execute(self, omaha_service) -> list[dict]  # compiles to SQL
```

- Immutable, chainable, lazy (no SQL until `.execute()`).
- Internally compiles to OmahaService.query_objects (keep OmahaService as backend).

### 2. Per-Object tool generator

`ObjectTypeToolFactory.build_tools(ontology) -> list[ToolSpec]`

For each confirmed ObjectType, emit 2 tools:

**`search_<ObjectName>`** — typed flat parameters:
- One param per filterable property, named `<field>` (eq) or `<field>_min/_max/_contains` for numeric/string.
- `sort_by`: enum of object's sortable fields, plus `_asc`/`_desc` suffix.
- `select`: array of field-name enum.
- `limit`: integer (default 100).

Example for `Product(sku, name, city, price)`:
```
search_Product(
  sku?: string,
  name?: string,
  name_contains?: string,
  city?: enum["北京", "上海", "深圳", ...],   # from value-type registry
  price_min?: number,
  price_max?: number,
  sort_by?: enum["sku", "name", "city", "price", "sku_desc", ...],
  select?: array<enum["sku", "name", "city", "price"]>,
  limit?: integer
)
```

**`count_<ObjectName>`** — same filter params, returns count only.

LLM never sees nested arrays of filter objects. Field names and enum values come from ontology.

### 3. Skill prompt update

Query skill stops mentioning `query_data`. Lists the available `search_*` / `count_*` tools (resolved at runtime from registry). Adds a one-liner: "Each ObjectType has its own search tool — pick the one matching the user's question."

### 4. Backwards-compatibility

Keep `query_data` registered for one release as fallback (Skill prompts no longer mention it). Remove after Stage 2 ships.

---

## File structure

- `app/services/agent/objectset/__init__.py` — ObjectSet class, Filter, Sort
- `app/services/agent/objectset/compiler.py` — ObjectSet → OmahaService call
- `app/services/agent/tools/factory.py` — ObjectTypeToolFactory
- `app/services/agent/tools/factory_test.py` — unit tests
- `app/services/agent/chat_service.py` — wire factory into runtime (call once per session, register dynamically)
- `app/services/agent/skills/definitions/query.yaml` — prompt update

No changes to OmahaService, ontology models, or DB schema.

---

## Out of scope (future stages)

- Aggregation tool (`aggregate_<Object>`) — Stage 4
- Link traversal (`linked_orders_filter`) — Stage 3
- ObjectSet RID state machine — Stage 4
- Value-type registry with explicit enum values — Stage 2 (Stage 1 falls back to plain string for enum fields if registry unavailable)

---

## Acceptance criteria

1. `Project 10` has Product → registry contains `search_Product` and `count_Product`.
2. Tool schemas pass OpenAI strict validation (no nested array+object).
3. E2E test `filtered-query-cn`: "深圳的商品" → LLM calls `search_Product(city="深圳")` → returns only 深圳 rows.
4. E2E test `filtered-multi`: "深圳且价格大于 20" → LLM calls `search_Product(city="深圳", price_min=20)`.
5. E2E test `unknown-field`: LLM cannot call with bogus field (schema rejects at OpenAI side).
6. All existing 21/25 passing E2E scenarios still pass.
7. `query_data` legacy tool still works for backward compatibility.
