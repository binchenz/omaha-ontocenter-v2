# Phase 2a: AI Auto-Modeling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable automatic ontology generation from SQL databases — scan table structures, use LLM to infer business semantics, and write results to the ontology DB.

**Architecture:** SchemaScanner (SQLAlchemy inspect) feeds table metadata to OntologyInferrer (two-stage LLM + code-based FK matching), which produces structured ontology drafts. Three API endpoints (scan/infer/confirm) expose the flow. OntologyImporter is refactored to support both YAML and dict input with upsert semantics.

**Tech Stack:** FastAPI, SQLAlchemy inspect, OpenAI/Deepseek/Anthropic API, Pydantic v2, pytest

**Spec Reference:** `docs/superpowers/specs/2026-04-25-phase2a-auto-modeling-design.md`

---

## File Structure

### New Files
- `backend/app/services/schema_scanner.py` — SQLAlchemy-based table scanning and sampling
- `backend/app/services/ontology_inferrer.py` — LLM inference (classify + infer + FK match)
- `backend/app/schemas/auto_model.py` — Pydantic request/response models
- `backend/tests/test_schema_scanner.py` — Scanner tests with in-memory SQLite
- `backend/tests/test_ontology_inferrer.py` — Inferrer tests with mocked LLM
- `backend/tests/test_api_auto_model.py` — API endpoint tests
- `backend/tests/integration/test_auto_model_e2e.py` — End-to-end flow test

### Modified Files
- `backend/app/services/ontology_importer.py` — Extract `import_dict()`, add upsert support
- `backend/app/api/ontology_store_routes.py` — Add scan/infer/confirm endpoints
- `backend/app/config.py` — Add inference config settings

---

## Task 1: Pydantic Schemas for Auto-Modeling

**Files:**
- Create: `backend/app/schemas/auto_model.py`

- [ ] **Step 1: Create the schemas file**

```python
# backend/app/schemas/auto_model.py
from pydantic import BaseModel, Field
from typing import Literal


SEMANTIC_TYPES = [
    "text", "number", "integer", "float", "boolean",
    "date", "datetime", "timestamp",
    "currency_cny", "currency_usd",
    "percentage", "ratio",
    "phone", "email", "address", "province", "city",
    "order_status", "approval_status",
    "quantity", "weight_kg", "weight_g", "volume_l",
    "stock_code", "url", "id",
]


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool = True

class TableSummaryResponse(BaseModel):
    name: str
    row_count: int
    columns: list[ColumnInfo]
    sample_values: dict[str, list[str]]

class ScanRequest(BaseModel):
    datasource_id: str

class ScanResponse(BaseModel):
    tables: list[TableSummaryResponse]

class InferRequest(BaseModel):
    datasource_id: str
    tables: list[str]

class TableClassification(BaseModel):
    name: str
    category: Literal["business", "system", "temporary", "unknown"] = "unknown"
    confidence: float = 0.5
    description: str = ""

class InferredProperty(BaseModel):
    name: str
    data_type: str
    semantic_type: str | None = None
    description: str = ""
    is_computed: bool = False
    expression: str | None = None

class InferredObject(BaseModel):
    name: str
    source_entity: str
    description: str = ""
    business_context: str = ""
    domain: str = ""
    datasource_id: str = ""
    datasource_type: str = "sql"
    properties: list[InferredProperty] = []
    suggested_health_rules: list[dict] = []
    suggested_computed_properties: list[dict] = []

class InferredRelationship(BaseModel):
    name: str
    from_object: str
    to_object: str
    relationship_type: str = "many_to_one"
    from_field: str
    to_field: str = "id"

class InferResponse(BaseModel):
    objects: list[InferredObject]
    relationships: list[InferredRelationship] = []
    warnings: list[str] = []

class ConfirmRequest(BaseModel):
    objects: list[InferredObject]
    relationships: list[InferredRelationship] = []

class ConfirmResponse(BaseModel):
    objects_created: int = 0
    objects_updated: int = 0
    relationships_created: int = 0
```

- [ ] **Step 2: Verify import works**

Run: `cd backend && python -c "from app.schemas.auto_model import ScanRequest, InferResponse, ConfirmRequest; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/auto_model.py
git commit -m "feat(phase2a): add Pydantic schemas for auto-modeling API"
```

---

## Task 2: SchemaScanner Service

**Files:**
- Create: `backend/app/services/schema_scanner.py`
- Test: `backend/tests/test_schema_scanner.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_schema_scanner.py
import pytest
from sqlalchemy import create_engine, text
from app.services.schema_scanner import SchemaScanner, TableSummary


@pytest.fixture
def test_db_url():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE t_order (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                total_amount REAL,
                status TEXT,
                created_at TEXT
            )
        """))
        conn.execute(text("""
            INSERT INTO t_order VALUES
            (1, 101, 299.00, 'pending', '2024-01-15'),
            (2, 102, 1580.50, 'shipped', '2024-02-20'),
            (3, 101, 45.00, 'delivered', '2024-03-10'),
            (4, 103, 890.00, 'cancelled', '2024-04-05'),
            (5, 102, 320.00, 'pending', '2024-05-01')
        """))
        conn.execute(text("""
            CREATE TABLE t_customer (
                id INTEGER PRIMARY KEY,
                name TEXT,
                phone TEXT,
                region TEXT
            )
        """))
        conn.execute(text("""
            INSERT INTO t_customer VALUES
            (101, 'Alice', '13800001111', 'East'),
            (102, 'Bob', '13900002222', 'West'),
            (103, 'Charlie', '13700003333', 'East')
        """))
        conn.execute(text("""
            CREATE TABLE django_migrations (
                id INTEGER PRIMARY KEY,
                app TEXT,
                name TEXT
            )
        """))
        conn.commit()
    return engine.url


def test_list_tables(test_db_url):
    scanner = SchemaScanner(str(test_db_url))
    tables = scanner.list_tables()
    assert "t_order" in tables
    assert "t_customer" in tables
    assert "django_migrations" in tables


def test_scan_table_columns(test_db_url):
    scanner = SchemaScanner(str(test_db_url))
    summary = scanner.scan_table("t_order")
    assert isinstance(summary, TableSummary)
    assert summary.name == "t_order"
    col_names = [c["name"] for c in summary.columns]
    assert "id" in col_names
    assert "total_amount" in col_names
    assert "status" in col_names


def test_scan_table_row_count(test_db_url):
    scanner = SchemaScanner(str(test_db_url))
    summary = scanner.scan_table("t_order")
    assert summary.row_count == 5


def test_scan_table_sample_values(test_db_url):
    scanner = SchemaScanner(str(test_db_url))
    summary = scanner.scan_table("t_order")
    assert "status" in summary.sample_values
    status_values = summary.sample_values["status"]
    assert "pending" in status_values
    assert "shipped" in status_values


def test_scan_all(test_db_url):
    scanner = SchemaScanner(str(test_db_url))
    summaries = scanner.scan_all()
    assert len(summaries) == 3
    names = {s.name for s in summaries}
    assert names == {"t_order", "t_customer", "django_migrations"}


def test_scan_empty_table(test_db_url):
    engine = create_engine(str(test_db_url))
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE empty_table (id INTEGER PRIMARY KEY)"))
        conn.commit()
    scanner = SchemaScanner(str(test_db_url))
    summary = scanner.scan_table("empty_table")
    assert summary.row_count == 0
    assert summary.sample_values == {"id": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_schema_scanner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.schema_scanner'`

- [ ] **Step 3: Implement SchemaScanner**

```python
# backend/app/services/schema_scanner.py
from dataclasses import dataclass, field
from sqlalchemy import create_engine, inspect, text


@dataclass
class TableSummary:
    name: str
    row_count: int
    columns: list[dict]
    sample_values: dict[str, list[str]] = field(default_factory=dict)


class SchemaScanner:
    def __init__(self, connection_url: str):
        self.engine = create_engine(connection_url)

    def list_tables(self) -> list[str]:
        inspector = inspect(self.engine)
        return inspector.get_table_names()

    def scan_table(self, table_name: str) -> TableSummary:
        inspector = inspect(self.engine)
        columns = [
            {"name": c["name"], "type": str(c["type"]), "nullable": c.get("nullable", True)}
            for c in inspector.get_columns(table_name)
        ]
        row_count = self._get_row_count(table_name)
        samples = self._sample_values(table_name, columns)
        return TableSummary(
            name=table_name, row_count=row_count,
            columns=columns, sample_values=samples,
        )

    def scan_all(self) -> list[TableSummary]:
        return [self.scan_table(t) for t in self.list_tables()]

    def _get_row_count(self, table_name: str) -> int:
        with self.engine.connect() as conn:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            return result.scalar() or 0

    def _sample_values(self, table_name: str, columns: list[dict], limit: int = 500) -> dict[str, list[str]]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(f'SELECT * FROM "{table_name}" LIMIT :lim'),
                {"lim": limit},
            ).mappings().all()
        samples = {}
        for col in columns:
            col_name = col["name"]
            values = list(set(
                str(row[col_name]) for row in rows if row.get(col_name) is not None
            ))
            samples[col_name] = sorted(values)[:20]
        return samples

    def close(self):
        self.engine.dispose()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_schema_scanner.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/schema_scanner.py backend/tests/test_schema_scanner.py
git commit -m "feat(phase2a): add SchemaScanner with table listing, column inspection, and sampling"
```

---

## Task 3: OntologyInferrer — LLM Calling and JSON Parsing

**Files:**
- Create: `backend/app/services/ontology_inferrer.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_ontology_inferrer.py`

- [ ] **Step 1: Add inference config to settings**

In `backend/app/config.py`, add before `model_config`:

```python
    # Inference
    INFER_LLM_PROVIDER: str = "deepseek"
    INFER_MAX_RETRIES: int = 1
    INFER_TIMEOUT: int = 30
    INFER_SAMPLE_ROWS: int = 500
    INFER_DISTINCT_LIMIT: int = 20
```

- [ ] **Step 2: Write failing tests for LLM calling and JSON parsing**

```python
# backend/tests/test_ontology_inferrer.py
import pytest
import json
from unittest.mock import patch, MagicMock
from app.services.ontology_inferrer import OntologyInferrer
from app.services.schema_scanner import TableSummary
from app.schemas.auto_model import (
    TableClassification, InferredObject, InferredRelationship, SEMANTIC_TYPES,
)


MOCK_CLASSIFY_RESPONSE = json.dumps([
    {"name": "t_order", "category": "business", "confidence": 0.95, "description": "Order table"},
    {"name": "t_customer", "category": "business", "confidence": 0.9, "description": "Customer table"},
    {"name": "django_migrations", "category": "system", "confidence": 0.99, "description": "Django framework table"},
])

MOCK_INFER_RESPONSE = json.dumps({
    "name": "订单",
    "source_entity": "t_order",
    "description": "客户采购订单",
    "business_context": "记录客户的购买行为",
    "domain": "retail",
    "properties": [
        {"name": "id", "data_type": "integer", "semantic_type": "id", "description": "订单ID"},
        {"name": "customer_id", "data_type": "integer", "semantic_type": "id", "description": "客户ID"},
        {"name": "total_amount", "data_type": "float", "semantic_type": "currency_cny", "description": "订单金额"},
        {"name": "status", "data_type": "string", "semantic_type": "order_status", "description": "订单状态"},
        {"name": "created_at", "data_type": "datetime", "semantic_type": "datetime", "description": "创建时间"},
    ],
    "suggested_health_rules": [],
    "suggested_computed_properties": [],
})


@pytest.fixture
def inferrer():
    return OntologyInferrer()


@pytest.fixture
def sample_tables():
    return [
        TableSummary(
            name="t_order", row_count=5000,
            columns=[
                {"name": "id", "type": "INTEGER", "nullable": False},
                {"name": "customer_id", "type": "INTEGER", "nullable": True},
                {"name": "total_amount", "type": "REAL", "nullable": True},
                {"name": "status", "type": "TEXT", "nullable": True},
                {"name": "created_at", "type": "TEXT", "nullable": True},
            ],
            sample_values={
                "id": ["1", "2", "3"],
                "customer_id": ["101", "102", "103"],
                "total_amount": ["299.00", "1580.50", "45.00"],
                "status": ["pending", "shipped", "delivered", "cancelled"],
                "created_at": ["2024-01-15", "2024-02-20"],
            },
        ),
        TableSummary(
            name="t_customer", row_count=800,
            columns=[
                {"name": "id", "type": "INTEGER", "nullable": False},
                {"name": "name", "type": "TEXT", "nullable": True},
                {"name": "phone", "type": "TEXT", "nullable": True},
                {"name": "region", "type": "TEXT", "nullable": True},
            ],
            sample_values={
                "id": ["101", "102", "103"],
                "name": ["Alice", "Bob"],
                "phone": ["13800001111", "13900002222"],
                "region": ["East", "West"],
            },
        ),
    ]


def test_parse_json_from_llm_response(inferrer):
    raw = "Here is the result:\n" + MOCK_CLASSIFY_RESPONSE + "\nDone."
    parsed = inferrer._extract_json(raw)
    assert isinstance(parsed, list)
    assert len(parsed) == 3


def test_parse_json_clean_response(inferrer):
    parsed = inferrer._extract_json(MOCK_CLASSIFY_RESPONSE)
    assert isinstance(parsed, list)


def test_parse_json_invalid_returns_none(inferrer):
    parsed = inferrer._extract_json("This is not JSON at all")
    assert parsed is None


@patch.object(OntologyInferrer, "_call_llm")
def test_classify_tables(mock_llm, inferrer, sample_tables):
    mock_llm.return_value = MOCK_CLASSIFY_RESPONSE
    classifications = inferrer.classify_tables(sample_tables)
    assert len(classifications) == 3
    order_cls = next(c for c in classifications if c.name == "t_order")
    assert order_cls.category == "business"


@patch.object(OntologyInferrer, "_call_llm")
def test_infer_table(mock_llm, inferrer, sample_tables):
    mock_llm.return_value = MOCK_INFER_RESPONSE
    result = inferrer.infer_table(sample_tables[0], datasource_id="mysql_erp")
    assert result is not None
    assert result.name == "订单"
    assert result.source_entity == "t_order"
    assert len(result.properties) == 5
    amount_prop = next(p for p in result.properties if p.name == "total_amount")
    assert amount_prop.semantic_type == "currency_cny"


@patch.object(OntologyInferrer, "_call_llm")
def test_infer_table_bad_response_returns_none(mock_llm, inferrer, sample_tables):
    mock_llm.return_value = "I cannot process this request."
    result = inferrer.infer_table(sample_tables[0], datasource_id="mysql_erp")
    assert result is None


def test_infer_relationships_by_naming(inferrer):
    objects = [
        InferredObject(
            name="订单", source_entity="t_order",
            properties=[
                {"name": "id", "data_type": "integer"},
                {"name": "customer_id", "data_type": "integer"},
            ],
        ),
        InferredObject(
            name="客户", source_entity="t_customer",
            properties=[
                {"name": "id", "data_type": "integer"},
                {"name": "name", "data_type": "string"},
            ],
        ),
    ]
    rels = inferrer.infer_relationships_by_naming(objects)
    assert len(rels) == 1
    assert rels[0].from_object == "t_order"
    assert rels[0].to_object == "t_customer"
    assert rels[0].from_field == "customer_id"


def test_semantic_type_validation(inferrer):
    bad_response = json.dumps({
        "name": "Test", "source_entity": "t_test", "description": "test",
        "properties": [
            {"name": "price", "data_type": "float", "semantic_type": "money_amount"},
        ],
    })
    parsed = inferrer._extract_json(bad_response)
    obj = InferredObject.model_validate(parsed)
    cleaned = inferrer._validate_semantic_types(obj)
    assert cleaned.properties[0].semantic_type is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_ontology_inferrer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement OntologyInferrer**

```python
# backend/app/services/ontology_inferrer.py
import json
import re
from typing import Optional
from openai import OpenAI
from app.config import settings
from app.services.schema_scanner import TableSummary
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
6. properties: 为每个字段推断semantic_type，必须从以下列表中选择：
   {semantic_types}
   如果没有合适的类型，设为null

只输出JSON对象，不要其他文字。"""


class OntologyInferrer:
    def __init__(self):
        self.client = self._create_client()
        self.model = self._get_model()

    def _create_client(self) -> Optional[OpenAI]:
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
        for pattern in [r'\[[\s\S]*\]', r'\{[\s\S]*\}']:
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

    def infer_table(self, table: TableSummary, datasource_id: str) -> Optional[InferredObject]:
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ontology_inferrer.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ontology_inferrer.py backend/app/config.py backend/tests/test_ontology_inferrer.py
git commit -m "feat(phase2a): add OntologyInferrer with LLM classification, inference, and FK matching"
```

---

## Task 4: Refactor OntologyImporter — Extract import_dict() with Upsert

**Files:**
- Modify: `backend/app/services/ontology_importer.py`
- Test: `backend/tests/test_ontology_importer.py` (extend)

- [ ] **Step 1: Write failing test for import_dict and upsert**

Append to `backend/tests/test_ontology_importer.py`:

```python
def test_import_dict(db_session, tenant):
    importer = OntologyImporter(db_session)
    config = {
        "datasources": [{"id": "db1", "type": "sql"}],
        "ontology": {
            "objects": [
                {
                    "name": "Product",
                    "datasource": "db1",
                    "source_entity": "t_product",
                    "properties": [
                        {"name": "id", "type": "integer"},
                        {"name": "price", "type": "float", "semantic_type": "currency_cny"},
                    ],
                }
            ],
            "relationships": [],
        },
    }
    result = importer.import_dict(tenant_id=tenant.id, config=config)
    assert result["objects_created"] == 1


def test_import_dict_upsert(db_session, tenant):
    importer = OntologyImporter(db_session)
    config = {
        "datasources": [{"id": "db1", "type": "sql"}],
        "ontology": {
            "objects": [
                {
                    "name": "Product",
                    "datasource": "db1",
                    "source_entity": "t_product",
                    "properties": [{"name": "id", "type": "integer"}],
                }
            ],
            "relationships": [],
        },
    }
    importer.import_dict(tenant_id=tenant.id, config=config)

    config_v2 = {
        "datasources": [{"id": "db1", "type": "sql"}],
        "ontology": {
            "objects": [
                {
                    "name": "Product",
                    "datasource": "db1",
                    "source_entity": "t_product",
                    "properties": [
                        {"name": "id", "type": "integer"},
                        {"name": "price", "type": "float"},
                        {"name": "name", "type": "string"},
                    ],
                }
            ],
            "relationships": [],
        },
    }
    result = importer.import_dict(tenant_id=tenant.id, config=config_v2)
    assert result["objects_updated"] == 1
    assert result["objects_created"] == 0

    store = OntologyStore(db_session)
    product = store.get_object(tenant.id, "Product")
    assert len(product.properties) == 3


def test_import_yaml_calls_import_dict(db_session, tenant):
    importer = OntologyImporter(db_session)
    yaml_content = """
datasources:
  - id: db1
    type: sql
ontology:
  objects:
    - name: Item
      datasource: db1
      source_entity: t_item
      properties:
        - name: id
          type: integer
  relationships: []
"""
    result = importer.import_yaml(tenant_id=tenant.id, yaml_content=yaml_content)
    assert result["objects_created"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_ontology_importer.py::test_import_dict -v`
Expected: FAIL — `AttributeError: 'OntologyImporter' object has no attribute 'import_dict'`

- [ ] **Step 3: Refactor OntologyImporter**

Replace `backend/app/services/ontology_importer.py` with:

```python
# backend/app/services/ontology_importer.py
import yaml
from sqlalchemy.orm import Session
from app.services.ontology_store import OntologyStore


class OntologyImporter:
    def __init__(self, db: Session):
        self.db = db
        self.store = OntologyStore(db)

    def import_yaml(self, tenant_id: int, yaml_content: str) -> dict:
        if len(yaml_content) > 1_000_000:
            raise ValueError("YAML content exceeds 1MB limit")
        config = yaml.safe_load(yaml_content)
        if not isinstance(config, dict):
            raise ValueError("YAML must be a dictionary")
        return self.import_dict(tenant_id, config)

    def import_dict(self, tenant_id: int, config: dict) -> dict:
        ontology = config.get("ontology", {})
        datasources_list = config.get("datasources", [])
        if not isinstance(datasources_list, list):
            raise ValueError("datasources must be a list")
        datasources = {ds["id"]: ds for ds in datasources_list}

        objects_created = 0
        objects_updated = 0
        object_map = {}

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
                business_context=obj_def.get("business_context"),
                domain=obj_def.get("domain"),
                default_filters=obj_def.get("default_filters"),
            )
            object_map[obj_def["name"]] = obj

            for prop in obj_def.get("properties", []):
                self.store.add_property(
                    object_id=obj.id,
                    name=prop["name"],
                    data_type=prop.get("type", prop.get("data_type", "string")),
                    semantic_type=prop.get("semantic_type"),
                    description=prop.get("description"),
                )

            for cp in obj_def.get("computed_properties", []):
                self.store.add_property(
                    object_id=obj.id,
                    name=cp["name"],
                    data_type="float",
                    semantic_type=cp.get("semantic_type"),
                    description=cp.get("description"),
                    is_computed=True,
                    expression=cp.get("expression"),
                )

            for rule in obj_def.get("health_rules", []):
                self.store.add_health_rule(
                    object_id=obj.id,
                    metric=rule["metric"],
                    expression=rule["expression"],
                    warning_threshold=rule.get("warning"),
                    critical_threshold=rule.get("critical"),
                    advice=rule.get("advice"),
                )

            for goal in obj_def.get("goals", []):
                self.store.add_business_goal(
                    object_id=obj.id,
                    name=goal["name"],
                    metric=goal["metric"],
                    target=goal["target"],
                    period=goal.get("period"),
                )

            for dk in obj_def.get("domain_knowledge", []):
                self.store.add_domain_knowledge(object_id=obj.id, content=dk)

        relationships_created = 0
        for rel_def in ontology.get("relationships", []):
            from_obj = object_map.get(rel_def.get("from_object"))
            to_obj = object_map.get(rel_def.get("to_object"))
            if from_obj and to_obj:
                join = rel_def.get("join_condition", {})
                self.store.add_relationship(
                    tenant_id=tenant_id,
                    name=rel_def["name"],
                    from_object_id=from_obj.id,
                    to_object_id=to_obj.id,
                    relationship_type=rel_def.get("type", rel_def.get("relationship_type", "one_to_many")),
                    from_field=join.get("from_field", rel_def.get("from_field", "")),
                    to_field=join.get("to_field", rel_def.get("to_field", "")),
                    description=rel_def.get("description"),
                )
                relationships_created += 1

        self.db.commit()
        return {
            "objects_created": objects_created,
            "objects_updated": objects_updated,
            "relationships_created": relationships_created,
        }
```

- [ ] **Step 4: Run all importer tests**

Run: `cd backend && python -m pytest tests/test_ontology_importer.py -v`
Expected: All tests PASS (existing + 3 new)

- [ ] **Step 5: Run full test suite for regression**

Run: `cd backend && python -m pytest tests/ --ignore=tests/integration -v --tb=short`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ontology_importer.py backend/tests/test_ontology_importer.py
git commit -m "refactor(phase2a): extract import_dict() from OntologyImporter, add upsert support"
```

---

## Task 5: API Endpoints — scan, infer, confirm

**Files:**
- Modify: `backend/app/api/ontology_store_routes.py`
- Test: `backend/tests/test_api_auto_model.py`

- [ ] **Step 1: Write failing tests for the three endpoints**

```python
# backend/tests/test_api_auto_model.py
import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.models.project import Project
from app.services.schema_scanner import TableSummary


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db_session = Session()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    tenant = Tenant(name="Test Corp", plan="free")
    db_session.add(tenant)
    db_session.commit()

    user = User(email="auto@test.com", username="autotest", hashed_password="hashed", tenant_id=tenant.id)
    db_session.add(user)
    db_session.commit()

    project = Project(name="Auto Test", owner_id=user.id, tenant_id=tenant.id,
                      omaha_config="datasources:\n  - id: test_db\n    type: sql\n    connection:\n      url: sqlite:///:memory:")
    db_session.add(project)
    db_session.commit()

    from app.api.deps import get_current_user

    class FakeUser:
        def __init__(self, u):
            self.id = u.id
            self.email = u.email
            self.username = u.username
            self.tenant_id = u.tenant_id
            self.is_active = u.is_active
            self.is_superuser = u.is_superuser

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user)
    yield TestClient(app), project.id
    app.dependency_overrides.clear()
    db_session.close()


def test_scan_endpoint(client):
    test_client, project_id = client
    mock_tables = [
        TableSummary(name="t_order", row_count=100,
                     columns=[{"name": "id", "type": "INTEGER", "nullable": False}],
                     sample_values={"id": ["1", "2", "3"]}),
    ]
    with patch("app.api.ontology_store_routes.SchemaScanner") as MockScanner:
        MockScanner.return_value.scan_all.return_value = mock_tables
        MockScanner.return_value.close.return_value = None
        resp = test_client.post(
            f"/api/v1/ontology-store/{project_id}/scan",
            json={"datasource_id": "test_db"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tables"]) == 1
    assert data["tables"][0]["name"] == "t_order"


def test_infer_endpoint(client):
    test_client, project_id = client
    mock_tables = [
        TableSummary(name="t_order", row_count=100,
                     columns=[{"name": "id", "type": "INTEGER", "nullable": False}],
                     sample_values={"id": ["1", "2"]}),
    ]
    from app.schemas.auto_model import InferredObject, InferredProperty
    mock_obj = InferredObject(
        name="订单", source_entity="t_order", description="订单表",
        datasource_id="test_db", datasource_type="sql",
        properties=[InferredProperty(name="id", data_type="integer", semantic_type="id")],
    )
    with patch("app.api.ontology_store_routes.SchemaScanner") as MockScanner, \
         patch("app.api.ontology_store_routes.OntologyInferrer") as MockInferrer:
        MockScanner.return_value.scan_table.return_value = mock_tables[0]
        MockScanner.return_value.close.return_value = None
        MockInferrer.return_value.infer_table.return_value = mock_obj
        MockInferrer.return_value.infer_relationships_by_naming.return_value = []
        resp = test_client.post(
            f"/api/v1/ontology-store/{project_id}/infer",
            json={"datasource_id": "test_db", "tables": ["t_order"]},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["objects"]) == 1
    assert data["objects"][0]["name"] == "订单"


def test_confirm_endpoint(client):
    test_client, project_id = client
    resp = test_client.post(
        f"/api/v1/ontology-store/{project_id}/confirm",
        json={
            "objects": [
                {
                    "name": "订单",
                    "source_entity": "t_order",
                    "description": "订单表",
                    "datasource_id": "test_db",
                    "datasource_type": "sql",
                    "properties": [
                        {"name": "id", "data_type": "integer", "semantic_type": "id"},
                        {"name": "amount", "data_type": "float", "semantic_type": "currency_cny"},
                    ],
                }
            ],
            "relationships": [],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["objects_created"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_api_auto_model.py -v`
Expected: FAIL — 404 (endpoints not registered)

- [ ] **Step 3: Add scan/infer/confirm endpoints**

Append to `backend/app/api/ontology_store_routes.py`:

```python
from app.services.schema_scanner import SchemaScanner
from app.services.ontology_inferrer import OntologyInferrer
from app.schemas.auto_model import (
    ScanRequest, ScanResponse, TableSummaryResponse, ColumnInfo,
    InferRequest, InferResponse,
    ConfirmRequest, ConfirmResponse,
)


def _get_datasource_url(project, datasource_id: str) -> str:
    """Extract connection URL from project's YAML config for a given datasource_id."""
    import yaml
    config = yaml.safe_load(project.omaha_config or "")
    if not isinstance(config, dict):
        return ""
    for ds in config.get("datasources", []):
        if ds.get("id") == datasource_id:
            conn = ds.get("connection", {})
            return conn.get("url", "")
    return ""


@router.post("/{project_id}/scan", response_model=ScanResponse)
def scan_tables(
    project_id: int,
    request: ScanRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    url = _get_datasource_url(project, request.datasource_id)
    if not url:
        raise HTTPException(status_code=400, detail=f"Datasource '{request.datasource_id}' not found or has no URL")
    scanner = SchemaScanner(url)
    try:
        summaries = scanner.scan_all()
        tables = [
            TableSummaryResponse(
                name=s.name, row_count=s.row_count,
                columns=[ColumnInfo(name=c["name"], type=c["type"], nullable=c.get("nullable", True)) for c in s.columns],
                sample_values=s.sample_values,
            )
            for s in summaries
        ]
        return ScanResponse(tables=tables)
    finally:
        scanner.close()


@router.post("/{project_id}/infer", response_model=InferResponse)
def infer_ontology(
    project_id: int,
    request: InferRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    url = _get_datasource_url(project, request.datasource_id)
    if not url:
        raise HTTPException(status_code=400, detail=f"Datasource '{request.datasource_id}' not found or has no URL")

    scanner = SchemaScanner(url)
    inferrer = OntologyInferrer()
    try:
        objects = []
        warnings = []
        for table_name in request.tables:
            summary = scanner.scan_table(table_name)
            result = inferrer.infer_table(summary, datasource_id=request.datasource_id)
            if result:
                objects.append(result)
            else:
                warnings.append(f"表 {table_name} 推断失败，需手动配置")
        relationships = inferrer.infer_relationships_by_naming(objects)
        return InferResponse(objects=objects, relationships=relationships, warnings=warnings)
    finally:
        scanner.close()


@router.post("/{project_id}/confirm", response_model=ConfirmResponse)
def confirm_ontology(
    project_id: int,
    request: ConfirmRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tenant_id = _get_tenant_id(project)
    importer = OntologyImporter(db)
    config = {
        "datasources": [
            {"id": obj.datasource_id, "type": obj.datasource_type}
            for obj in request.objects
        ],
        "ontology": {
            "objects": [
                {
                    "name": obj.name,
                    "datasource": obj.datasource_id,
                    "source_entity": obj.source_entity,
                    "description": obj.description,
                    "business_context": obj.business_context,
                    "domain": obj.domain,
                    "properties": [
                        {"name": p.name, "type": p.data_type, "semantic_type": p.semantic_type, "description": p.description}
                        for p in obj.properties
                    ],
                }
                for obj in request.objects
            ],
            "relationships": [
                {
                    "name": r.name,
                    "from_object": r.from_object,
                    "to_object": r.to_object,
                    "type": r.relationship_type,
                    "from_field": r.from_field,
                    "to_field": r.to_field,
                }
                for r in request.relationships
            ],
        },
    }
    result = importer.import_dict(tenant_id=tenant_id, config=config)
    return ConfirmResponse(**result)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api_auto_model.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/ontology_store_routes.py backend/tests/test_api_auto_model.py
git commit -m "feat(phase2a): add scan/infer/confirm API endpoints for auto-modeling"
```

---

## Task 6: Integration Test — End-to-End Auto-Modeling Flow

**Files:**
- Create: `backend/tests/integration/test_auto_model_e2e.py`

- [ ] **Step 1: Write integration test**

```python
# backend/tests/integration/test_auto_model_e2e.py
"""
End-to-end: create SQLite tables → scan → mock LLM infer → confirm → verify ontology in DB.
"""
import json
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.tenant import Tenant
from app.services.schema_scanner import SchemaScanner
from app.services.ontology_inferrer import OntologyInferrer
from app.services.ontology_importer import OntologyImporter
from app.services.ontology_store import OntologyStore


@pytest.fixture
def setup():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    tenant = Tenant(name="E2E Corp", plan="free")
    db.add(tenant)
    db.commit()

    biz_engine = create_engine("sqlite:///:memory:")
    with biz_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE t_order (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                total_amount REAL,
                status TEXT
            )
        """))
        conn.execute(text("INSERT INTO t_order VALUES (1, 101, 500.0, 'pending')"))
        conn.execute(text("""
            CREATE TABLE t_customer (
                id INTEGER PRIMARY KEY,
                name TEXT,
                phone TEXT
            )
        """))
        conn.execute(text("INSERT INTO t_customer VALUES (101, 'Alice', '13800001111')"))
        conn.commit()

    yield db, tenant, biz_engine.url
    db.close()


MOCK_ORDER_INFER = json.dumps({
    "name": "订单", "source_entity": "t_order",
    "description": "客户订单", "business_context": "购买记录", "domain": "retail",
    "properties": [
        {"name": "id", "data_type": "integer", "semantic_type": "id"},
        {"name": "customer_id", "data_type": "integer", "semantic_type": "id"},
        {"name": "total_amount", "data_type": "float", "semantic_type": "currency_cny"},
        {"name": "status", "data_type": "string", "semantic_type": "order_status"},
    ],
})

MOCK_CUSTOMER_INFER = json.dumps({
    "name": "客户", "source_entity": "t_customer",
    "description": "客户信息", "business_context": "客户档案", "domain": "retail",
    "properties": [
        {"name": "id", "data_type": "integer", "semantic_type": "id"},
        {"name": "name", "data_type": "string", "semantic_type": "text"},
        {"name": "phone", "data_type": "string", "semantic_type": "phone"},
    ],
})


def test_full_auto_model_flow(setup):
    db, tenant, biz_url = setup

    # Step 1: Scan
    scanner = SchemaScanner(str(biz_url))
    summaries = scanner.scan_all()
    assert len(summaries) == 2
    table_names = {s.name for s in summaries}
    assert table_names == {"t_order", "t_customer"}
    scanner.close()

    # Step 2: Infer (mock LLM)
    inferrer = OntologyInferrer()
    infer_responses = {"t_order": MOCK_ORDER_INFER, "t_customer": MOCK_CUSTOMER_INFER}

    objects = []
    with patch.object(OntologyInferrer, "_call_llm") as mock_llm:
        for summary in summaries:
            mock_llm.return_value = infer_responses[summary.name]
            result = inferrer.infer_table(summary, datasource_id="biz_db")
            assert result is not None
            objects.append(result)

    assert len(objects) == 2

    # Step 3: FK matching
    relationships = inferrer.infer_relationships_by_naming(objects)
    assert len(relationships) == 1
    assert relationships[0].from_field == "customer_id"

    # Step 4: Confirm (write to DB)
    importer = OntologyImporter(db)
    config = {
        "datasources": [{"id": "biz_db", "type": "sql"}],
        "ontology": {
            "objects": [
                {
                    "name": obj.name,
                    "datasource": obj.datasource_id,
                    "source_entity": obj.source_entity,
                    "description": obj.description,
                    "domain": obj.domain,
                    "properties": [
                        {"name": p.name, "type": p.data_type, "semantic_type": p.semantic_type}
                        for p in obj.properties
                    ],
                }
                for obj in objects
            ],
            "relationships": [
                {
                    "name": r.name, "from_object": r.from_object, "to_object": r.to_object,
                    "type": r.relationship_type, "from_field": r.from_field, "to_field": r.to_field,
                }
                for r in relationships
            ],
        },
    }
    result = importer.import_dict(tenant_id=tenant.id, config=config)
    assert result["objects_created"] == 2
    assert result["relationships_created"] == 1

    # Step 5: Verify in DB
    store = OntologyStore(db)
    ontology = store.get_full_ontology(tenant.id)
    assert len(ontology["objects"]) == 2
    assert len(ontology["relationships"]) == 1

    order = next(o for o in ontology["objects"] if o["source_entity"] == "t_order")
    assert order["name"] == "订单"
    assert any(p["semantic_type"] == "currency_cny" for p in order["properties"])

    # Step 6: Verify upsert works
    result2 = importer.import_dict(tenant_id=tenant.id, config=config)
    assert result2["objects_updated"] == 2
    assert result2["objects_created"] == 0
```

- [ ] **Step 2: Run integration test**

Run: `cd backend && python -m pytest tests/integration/test_auto_model_e2e.py -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `cd backend && python -m pytest tests/ --ignore=tests/integration/test_phase31_mcp.py -v --tb=short`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/integration/test_auto_model_e2e.py
git commit -m "test(phase2a): add end-to-end auto-modeling integration test"
```
