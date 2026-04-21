# Connector Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded data source handling in OmahaService with a pluggable Connector framework, then add CSV/Excel and REST API connectors.

**Architecture:** Each data source type becomes a Connector class implementing `BaseConnector`. A registry maps YAML `type` strings to Connector classes. `OmahaService.query_objects()` delegates to the registry instead of branching on type. New connectors (CSV, REST) are added as plugins without touching core logic.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, pandas (CSV/Excel), httpx (REST API), pytest

---

## File Structure

### New files
- `backend/app/connectors/__init__.py` — auto-registration of all connectors
- `backend/app/connectors/base.py` — `BaseConnector` ABC + `ColumnDef` dataclass
- `backend/app/connectors/registry.py` — type→class mapping, `get_connector()`
- `backend/app/connectors/sql_connector.py` — PostgreSQL/MySQL/SQLite (extracted from omaha.py lines 382-668)
- `backend/app/connectors/tushare_connector.py` — Tushare Pro API (extracted from omaha.py lines 411-644)
- `backend/app/connectors/csv_connector.py` — CSV/Excel upload → import to SQLite
- `backend/app/connectors/rest_connector.py` — Generic REST API connector
- `backend/app/api/datasources.py` — New API endpoints for datasource management
- `backend/tests/test_connector_base.py` — Base + registry tests
- `backend/tests/test_connector_sql.py` — SQL connector tests
- `backend/tests/test_connector_tushare.py` — Tushare connector tests
- `backend/tests/test_connector_csv.py` — CSV connector tests
- `backend/tests/test_connector_rest.py` — REST connector tests
- `backend/tests/test_api_datasources.py` — Datasource API endpoint tests
- `frontend/src/pages/DatasourceManager.tsx` — Settings datasource tab
- `frontend/src/services/datasource.ts` — Datasource API client

### Modified files
- `backend/app/services/omaha.py` — Remove data source logic, delegate to connectors
- `backend/app/main.py` — Register datasource API router
- `backend/requirements.txt` — Add pandas, openpyxl
- `frontend/src/pages/Settings.tsx` — Add datasource tab

---

## Task 1: BaseConnector + Registry

**Files:**
- Create: `backend/app/connectors/__init__.py`
- Create: `backend/app/connectors/base.py`
- Create: `backend/app/connectors/registry.py`
- Test: `backend/tests/test_connector_base.py`

- [ ] **Step 1: Write failing tests for BaseConnector and registry**

```python
# backend/tests/test_connector_base.py
import pytest
from app.connectors.base import BaseConnector, ColumnDef
from app.connectors.registry import register, get_connector, _CONNECTORS


class FakeConnector(BaseConnector):
    def test_connection(self) -> bool:
        return self.config.get("valid", True)

    def discover_schema(self, source: str) -> list[ColumnDef]:
        return [ColumnDef(name="id", type="integer", nullable=False)]

    def query(self, source, columns=None, filters=None, limit=None):
        return [{"id": 1, "name": "test"}]


class TestColumnDef:
    def test_defaults(self):
        col = ColumnDef(name="price", type="decimal")
        assert col.nullable is True
        assert col.description == ""

    def test_all_fields(self):
        col = ColumnDef(name="ts_code", type="string", nullable=False, description="股票代码")
        assert col.name == "ts_code"
        assert col.nullable is False


class TestBaseConnector:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseConnector(config={})

    def test_concrete_implementation(self):
        conn = FakeConnector(config={"valid": True})
        assert conn.test_connection() is True
        assert len(conn.discover_schema("test")) == 1
        assert conn.query("test")[0]["id"] == 1

    def test_close_is_noop_by_default(self):
        conn = FakeConnector(config={})
        conn.close()  # should not raise


class TestRegistry:
    def setup_method(self):
        _CONNECTORS.clear()

    def test_register_and_get(self):
        register("fake", FakeConnector)
        conn = get_connector("fake", {"valid": True})
        assert isinstance(conn, FakeConnector)
        assert conn.test_connection() is True

    def test_get_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown datasource type"):
            get_connector("nonexistent", {})

    def test_register_multiple_types_same_class(self):
        register("type_a", FakeConnector)
        register("type_b", FakeConnector)
        assert isinstance(get_connector("type_a", {}), FakeConnector)
        assert isinstance(get_connector("type_b", {}), FakeConnector)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/test_connector_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.connectors'`

- [ ] **Step 3: Implement BaseConnector, ColumnDef, and registry**

```python
# backend/app/connectors/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ColumnDef:
    name: str
    type: str
    nullable: bool = True
    description: str = ""


class BaseConnector(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def test_connection(self) -> bool: ...

    @abstractmethod
    def discover_schema(self, source: str) -> list[ColumnDef]: ...

    @abstractmethod
    def query(
        self,
        source: str,
        columns: list[str] | None = None,
        filters: list[dict] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...

    def close(self) -> None:
        pass
```

```python
# backend/app/connectors/registry.py
from typing import Type
from app.connectors.base import BaseConnector

_CONNECTORS: dict[str, Type[BaseConnector]] = {}


def register(type_name: str, cls: Type[BaseConnector]):
    _CONNECTORS[type_name] = cls


def get_connector(type_name: str, config: dict) -> BaseConnector:
    cls = _CONNECTORS.get(type_name)
    if not cls:
        raise ValueError(f"Unknown datasource type: {type_name}")
    return cls(config)
```

```python
# backend/app/connectors/__init__.py
# Connectors are registered by importing this package.
# Individual connector modules call register() at import time.
# Registration happens in the task that implements each connector.
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/test_connector_base.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/ backend/tests/test_connector_base.py
git commit -m "feat: add BaseConnector ABC, ColumnDef, and connector registry"
```

---

## Task 2: SQLConnector (extract from omaha.py)

**Files:**
- Create: `backend/app/connectors/sql_connector.py`
- Test: `backend/tests/test_connector_sql.py`

- [ ] **Step 1: Write failing tests for SQLConnector**

```python
# backend/tests/test_connector_sql.py
import os
import sqlite3
import pytest
from app.connectors.sql_connector import SQLConnector
from app.connectors.base import ColumnDef


@pytest.fixture
def test_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)")
    conn.execute("INSERT INTO products VALUES (1, 'Widget', 9.99)")
    conn.execute("INSERT INTO products VALUES (2, 'Gadget', 19.99)")
    conn.execute("INSERT INTO products VALUES (3, 'Doohickey', 4.99)")
    conn.commit()
    conn.close()
    return db_path


class TestSQLConnector:
    def test_test_connection_sqlite(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        assert conn.test_connection() is True

    def test_test_connection_bad_path(self):
        conn = SQLConnector({"type": "sqlite", "database": "/nonexistent/path.db"})
        assert conn.test_connection() is False

    def test_discover_schema(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        cols = conn.discover_schema("products")
        names = [c.name for c in cols]
        assert "id" in names
        assert "name" in names
        assert "price" in names
        conn.close()

    def test_query_all(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        rows = conn.query("products")
        assert len(rows) == 3
        assert rows[0]["name"] == "Widget"
        conn.close()

    def test_query_with_columns(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        rows = conn.query("products", columns=["name", "price"])
        assert set(rows[0].keys()) == {"name", "price"}
        conn.close()

    def test_query_with_filter(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        rows = conn.query("products", filters=[{"field": "price", "operator": ">", "value": "10"}])
        assert len(rows) == 1
        assert rows[0]["name"] == "Gadget"
        conn.close()

    def test_query_with_limit(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        rows = conn.query("products", limit=2)
        assert len(rows) == 2
        conn.close()

    def test_query_with_eq_filter(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        rows = conn.query("products", filters=[{"field": "name", "operator": "=", "value": "Widget"}])
        assert len(rows) == 1
        assert rows[0]["price"] == 9.99
        conn.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/test_connector_sql.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.connectors.sql_connector'`

- [ ] **Step 3: Implement SQLConnector**

Extract connection and query logic from `omaha.py` lines 382-668 into a standalone connector:

```python
# backend/app/connectors/sql_connector.py
import os
import sqlite3
from typing import Any

import pymysql
import pymysql.cursors

from app.connectors.base import BaseConnector, ColumnDef

OPERATOR_MAP = {"=", ">", "<", ">=", "<=", "!=", "LIKE", "IN", "IS NULL", "IS NOT NULL"}


class SQLConnector(BaseConnector):
    def test_connection(self) -> bool:
        try:
            conn = self._connect()
            conn.close()
            return True
        except Exception:
            return False

    def discover_schema(self, source: str) -> list[ColumnDef]:
        conn = self._connect()
        try:
            if self._db_type() == "sqlite":
                cursor = conn.execute(f"PRAGMA table_info({source})")
                return [
                    ColumnDef(name=row[1], type=self._map_sqlite_type(row[2]), nullable=not row[3])
                    for row in cursor.fetchall()
                ]
            else:
                cursor = conn.cursor()
                cursor.execute(f"DESCRIBE {source}")
                return [
                    ColumnDef(name=row[0], type=self._map_mysql_type(row[1]), nullable=row[2] == "YES")
                    for row in cursor.fetchall()
                ]
        finally:
            conn.close()

    def query(self, source, columns=None, filters=None, limit=None):
        col_clause = ", ".join(columns) if columns else "*"
        query_str = f"SELECT {col_clause} FROM {source}"
        params: list[Any] = []

        if filters:
            where_parts = []
            for f in filters:
                op = f.get("operator", "=")
                if op in ("IS NULL", "IS NOT NULL"):
                    where_parts.append(f"{f['field']} {op}")
                elif op == "IN":
                    vals = [v.strip() for v in str(f["value"]).split(",")]
                    placeholders = ", ".join([self._placeholder()] * len(vals))
                    where_parts.append(f"{f['field']} IN ({placeholders})")
                    params.extend(vals)
                else:
                    where_parts.append(f"{f['field']} {op} {self._placeholder()}")
                    params.append(f["value"])
            if where_parts:
                query_str += " WHERE " + " AND ".join(where_parts)

        if limit:
            query_str += f" LIMIT {int(limit)}"

        return self._execute(query_str, params)

    def close(self) -> None:
        pass

    def _db_type(self) -> str:
        return self.config.get("type", "sqlite")

    def _placeholder(self) -> str:
        return "?" if self._db_type() == "sqlite" else "%s"

    def _connect(self):
        db_type = self._db_type()
        if db_type == "sqlite":
            db_path = self.config.get("database", "")
            if not os.path.isabs(db_path):
                db_path = os.path.abspath(db_path)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn
        return pymysql.connect(
            host=self.config.get("host"),
            port=self.config.get("port", 3306),
            user=self.config.get("user"),
            password=self.config.get("password"),
            database=self.config.get("database"),
            connect_timeout=10,
            charset="utf8mb4",
        )

    def _execute(self, query_str: str, params: list) -> list[dict]:
        conn = self._connect()
        try:
            if self._db_type() == "sqlite":
                cursor = conn.cursor()
                cursor.execute(query_str, params)
                return [dict(row) for row in cursor.fetchall()]
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query_str, params)
            return [
                {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in row.items()}
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    @staticmethod
    def _map_sqlite_type(t: str) -> str:
        t = t.upper()
        if "INT" in t:
            return "integer"
        if "REAL" in t or "FLOAT" in t or "DOUBLE" in t:
            return "decimal"
        if "TEXT" in t or "CHAR" in t or "CLOB" in t:
            return "string"
        if "BLOB" in t:
            return "string"
        return "string"

    @staticmethod
    def _map_mysql_type(t: str) -> str:
        t = t.lower()
        if "int" in t:
            return "integer"
        if any(x in t for x in ("decimal", "float", "double", "numeric")):
            return "decimal"
        if "date" in t:
            return "date"
        if "time" in t:
            return "datetime"
        return "string"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/test_connector_sql.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/sql_connector.py backend/tests/test_connector_sql.py
git commit -m "feat: add SQLConnector for PostgreSQL/MySQL/SQLite"
```

---

## Task 3: TushareConnector (extract from omaha.py)

**Files:**
- Create: `backend/app/connectors/tushare_connector.py`
- Test: `backend/tests/test_connector_tushare.py`

- [ ] **Step 1: Write failing tests for TushareConnector**

```python
# backend/tests/test_connector_tushare.py
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from app.connectors.tushare_connector import TushareConnector
from app.connectors.base import ColumnDef


@pytest.fixture
def tushare_config():
    return {"token": "test_token_123"}


@pytest.fixture
def obj_def():
    return {
        "api_name": "stock_basic",
        "properties": [
            {"name": "ts_code", "column": "ts_code", "type": "string"},
            {"name": "name", "column": "name", "type": "string"},
            {"name": "industry", "column": "industry", "type": "string"},
        ],
    }


class TestTushareConnector:
    @patch("app.connectors.tushare_connector.ts")
    def test_test_connection_success(self, mock_ts, tushare_config):
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.stock_basic.return_value = pd.DataFrame({"ts_code": ["000001.SZ"]})

        conn = TushareConnector(tushare_config)
        assert conn.test_connection() is True

    @patch("app.connectors.tushare_connector.ts")
    def test_test_connection_bad_token(self, mock_ts, tushare_config):
        mock_ts.pro_api.side_effect = Exception("Invalid token")
        conn = TushareConnector(tushare_config)
        assert conn.test_connection() is False

    def test_discover_schema_from_properties(self, tushare_config, obj_def):
        conn = TushareConnector(tushare_config)
        cols = conn.discover_schema("stock_basic", properties=obj_def["properties"])
        assert len(cols) == 3
        assert cols[0].name == "ts_code"
        assert cols[0].type == "string"

    @patch("app.connectors.tushare_connector.ts")
    def test_query_basic(self, mock_ts, tushare_config):
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.stock_basic.return_value = pd.DataFrame({
            "ts_code": ["000001.SZ", "600000.SH"],
            "name": ["平安银行", "浦发银行"],
            "industry": ["银行", "银行"],
        })

        conn = TushareConnector(tushare_config)
        rows = conn.query(
            source="stock_basic",
            columns=["ts_code", "name"],
            limit=2,
        )
        assert len(rows) == 2
        assert rows[0]["ts_code"] == "000001.SZ"

    @patch("app.connectors.tushare_connector.ts")
    def test_query_with_api_filter(self, mock_ts, tushare_config):
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.stock_basic.return_value = pd.DataFrame({
            "ts_code": ["000001.SZ"],
            "name": ["平安银行"],
        })

        conn = TushareConnector(tushare_config)
        rows = conn.query(
            source="stock_basic",
            filters=[{"field": "ts_code", "operator": "=", "value": "000001.SZ"}],
        )
        mock_pro.stock_basic.assert_called_once()
        call_kwargs = mock_pro.stock_basic.call_args[1]
        assert call_kwargs.get("ts_code") == "000001.SZ"

    @patch("app.connectors.tushare_connector.ts")
    def test_query_with_client_side_filter(self, mock_ts, tushare_config):
        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro
        mock_pro.stock_basic.return_value = pd.DataFrame({
            "ts_code": ["000001.SZ", "600000.SH"],
            "name": ["平安银行", "浦发银行"],
            "industry": ["银行", "银行"],
        })

        conn = TushareConnector(tushare_config)
        rows = conn.query(
            source="stock_basic",
            filters=[{"field": "name", "operator": "=", "value": "平安银行"}],
        )
        assert len(rows) == 1
        assert rows[0]["name"] == "平安银行"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/test_connector_tushare.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.connectors.tushare_connector'`

- [ ] **Step 3: Implement TushareConnector**

Extract Tushare logic from `omaha.py` lines 411-644:

```python
# backend/app/connectors/tushare_connector.py
from typing import Any
import tushare as ts
import pandas as pd
from app.connectors.base import BaseConnector, ColumnDef

SUPPORTED_PARAMS = {
    "stock_basic": ["ts_code", "name", "market", "list_status", "exchange"],
    "daily": ["ts_code", "trade_date", "start_date", "end_date"],
    "income": ["ts_code", "period", "start_date", "end_date", "report_type"],
    "balancesheet": ["ts_code", "period", "start_date", "end_date", "report_type"],
    "cashflow": ["ts_code", "period", "start_date", "end_date", "report_type"],
    "fina_indicator": ["ts_code", "period", "start_date", "end_date"],
    "daily_basic": ["ts_code", "trade_date", "start_date", "end_date"],
    "index_member_all": ["index_code"],
    "index_classify": ["src"],
    "stk_factor": ["ts_code", "trade_date", "start_date", "end_date"],
}


class TushareConnector(BaseConnector):
    def test_connection(self) -> bool:
        try:
            pro = ts.pro_api(self.config["token"])
            df = pro.stock_basic(ts_code="000001.SZ", fields="ts_code")
            return len(df) > 0
        except Exception:
            return False

    def discover_schema(self, source: str, properties: list[dict] | None = None) -> list[ColumnDef]:
        if not properties:
            return []
        return [
            ColumnDef(
                name=p.get("name", p.get("column", "")),
                type=p.get("type", "string"),
                description=p.get("description", ""),
            )
            for p in properties
        ]

    def query(self, source, columns=None, filters=None, limit=None):
        pro = ts.pro_api(self.config["token"])
        api_func = getattr(pro, source)

        api_params = {}
        client_filters = []
        supported = SUPPORTED_PARAMS.get(source, [])

        for f in (filters or []):
            field = f.get("field", "")
            value = f.get("value", "")
            op = f.get("operator", "=")
            if field in supported and op == "=":
                api_params[field] = value
            else:
                client_filters.append(f)

        fields_param = ",".join(columns) if columns else None
        if fields_param:
            api_params["fields"] = fields_param

        df = api_func(**api_params)

        for f in client_filters:
            field, op, value = f["field"], f.get("operator", "="), f["value"]
            if field not in df.columns:
                continue
            if op == "=":
                df = df[df[field].astype(str) == str(value)]
            elif op == ">":
                df = df[pd.to_numeric(df[field], errors="coerce") > float(value)]
            elif op == "<":
                df = df[pd.to_numeric(df[field], errors="coerce") < float(value)]
            elif op == ">=":
                df = df[pd.to_numeric(df[field], errors="coerce") >= float(value)]
            elif op == "<=":
                df = df[pd.to_numeric(df[field], errors="coerce") <= float(value)]

        if limit:
            df = df.head(limit)

        return df.to_dict("records")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/test_connector_tushare.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/tushare_connector.py backend/tests/test_connector_tushare.py
git commit -m "feat: add TushareConnector for Tushare Pro API"
```

---

## Task 4: CSVConnector

**Files:**
- Create: `backend/app/connectors/csv_connector.py`
- Modify: `backend/requirements.txt` — add pandas, openpyxl
- Test: `backend/tests/test_connector_csv.py`

- [ ] **Step 1: Add pandas and openpyxl to requirements**

Add to `backend/requirements.txt`:
```
pandas==2.2.3
openpyxl==3.1.5
```

Run: `cd backend && ./venv311/bin/pip install pandas openpyxl`

- [ ] **Step 2: Write failing tests for CSVConnector**

```python
# backend/tests/test_connector_csv.py
import os
import pytest
import csv
from app.connectors.csv_connector import CSVConnector
from app.connectors.base import ColumnDef


@pytest.fixture
def csv_file(tmp_path):
    path = str(tmp_path / "sales.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "product", "amount", "date"])
        writer.writerow(["1", "Widget", "99.5", "2024-01-15"])
        writer.writerow(["2", "Gadget", "149.0", "2024-01-16"])
        writer.writerow(["3", "Widget", "99.5", "2024-01-17"])
    return path


@pytest.fixture
def csv_connector(tmp_path, csv_file):
    db_path = str(tmp_path / "imported.db")
    return CSVConnector({"storage_path": str(tmp_path), "database": db_path})


class TestCSVConnector:
    def test_ingest_csv(self, csv_connector, csv_file):
        cols = csv_connector.ingest(csv_file, "sales")
        names = [c.name for c in cols]
        assert "order_id" in names
        assert "amount" in names
        assert len(cols) == 4

    def test_query_after_ingest(self, csv_connector, csv_file):
        csv_connector.ingest(csv_file, "sales")
        rows = csv_connector.query("sales")
        assert len(rows) == 3
        assert rows[0]["product"] == "Widget"

    def test_query_with_columns(self, csv_connector, csv_file):
        csv_connector.ingest(csv_file, "sales")
        rows = csv_connector.query("sales", columns=["product", "amount"])
        assert set(rows[0].keys()) == {"product", "amount"}

    def test_query_with_filter(self, csv_connector, csv_file):
        csv_connector.ingest(csv_file, "sales")
        rows = csv_connector.query("sales", filters=[{"field": "product", "operator": "=", "value": "Widget"}])
        assert len(rows) == 2

    def test_query_with_limit(self, csv_connector, csv_file):
        csv_connector.ingest(csv_file, "sales")
        rows = csv_connector.query("sales", limit=1)
        assert len(rows) == 1

    def test_discover_schema_after_ingest(self, csv_connector, csv_file):
        csv_connector.ingest(csv_file, "sales")
        cols = csv_connector.discover_schema("sales")
        assert len(cols) == 4

    def test_test_connection(self, csv_connector, csv_file):
        csv_connector.ingest(csv_file, "sales")
        assert csv_connector.test_connection() is True

    def test_test_connection_no_db(self, tmp_path):
        conn = CSVConnector({"storage_path": str(tmp_path), "database": str(tmp_path / "nonexistent.db")})
        assert conn.test_connection() is False
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/test_connector_csv.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.connectors.csv_connector'`

- [ ] **Step 4: Implement CSVConnector**

```python
# backend/app/connectors/csv_connector.py
import os
import pandas as pd
from app.connectors.base import BaseConnector, ColumnDef
from app.connectors.sql_connector import SQLConnector


class CSVConnector(BaseConnector):
    def _db_path(self) -> str:
        return self.config.get("database", "")

    def _sql(self) -> SQLConnector:
        return SQLConnector({"type": "sqlite", "database": self._db_path()})

    def test_connection(self) -> bool:
        return os.path.exists(self._db_path())

    def discover_schema(self, source: str) -> list[ColumnDef]:
        return self._sql().discover_schema(source)

    def query(self, source, columns=None, filters=None, limit=None):
        return self._sql().query(source, columns, filters, limit)

    def ingest(self, file_path: str, table_name: str) -> list[ColumnDef]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        from sqlalchemy import create_engine
        engine = create_engine(f"sqlite:///{self._db_path()}")
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        engine.dispose()

        return self._infer_schema(df)

    @staticmethod
    def _infer_schema(df: pd.DataFrame) -> list[ColumnDef]:
        type_map = {"int64": "integer", "float64": "decimal", "object": "string", "bool": "boolean"}
        return [
            ColumnDef(
                name=col,
                type=type_map.get(str(df[col].dtype), "string"),
                nullable=bool(df[col].isnull().any()),
            )
            for col in df.columns
        ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/test_connector_csv.py -v`
Expected: All 8 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/connectors/csv_connector.py backend/tests/test_connector_csv.py backend/requirements.txt
git commit -m "feat: add CSVConnector for CSV/Excel file import"
```

---

## Task 5: RESTConnector

**Files:**
- Create: `backend/app/connectors/rest_connector.py`
- Test: `backend/tests/test_connector_rest.py`

- [ ] **Step 1: Write failing tests for RESTConnector**

```python
# backend/tests/test_connector_rest.py
import pytest
from unittest.mock import patch, MagicMock
import httpx
from app.connectors.rest_connector import RESTConnector


@pytest.fixture
def rest_config():
    return {
        "base_url": "https://api.example.com/v1",
        "auth_type": "bearer",
        "token": "test_token",
    }


def mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


class TestRESTConnector:
    @patch("app.connectors.rest_connector.httpx.get")
    def test_query_basic(self, mock_get, rest_config):
        mock_get.return_value = mock_response([
            {"id": 1, "name": "Order A"},
            {"id": 2, "name": "Order B"},
        ])
        conn = RESTConnector(rest_config)
        rows = conn.query("orders")
        assert len(rows) == 2
        assert rows[0]["name"] == "Order A"
        mock_get.assert_called_once()

    @patch("app.connectors.rest_connector.httpx.get")
    def test_query_with_response_path(self, mock_get, rest_config):
        rest_config["response_path"] = "data.items"
        mock_get.return_value = mock_response({
            "data": {"items": [{"id": 1}, {"id": 2}], "total": 2}
        })
        conn = RESTConnector(rest_config)
        rows = conn.query("orders")
        assert len(rows) == 2

    @patch("app.connectors.rest_connector.httpx.get")
    def test_query_with_columns(self, mock_get, rest_config):
        mock_get.return_value = mock_response([
            {"id": 1, "name": "A", "price": 10},
        ])
        conn = RESTConnector(rest_config)
        rows = conn.query("orders", columns=["id", "name"])
        assert set(rows[0].keys()) == {"id", "name"}

    @patch("app.connectors.rest_connector.httpx.get")
    def test_query_with_limit(self, mock_get, rest_config):
        mock_get.return_value = mock_response([{"id": i} for i in range(10)])
        conn = RESTConnector(rest_config)
        rows = conn.query("orders", limit=3)
        assert len(rows) == 3

    @patch("app.connectors.rest_connector.httpx.get")
    def test_auth_bearer(self, mock_get, rest_config):
        mock_get.return_value = mock_response([])
        conn = RESTConnector(rest_config)
        conn.query("orders")
        headers = mock_get.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test_token"

    @patch("app.connectors.rest_connector.httpx.get")
    def test_auth_api_key(self, mock_get):
        config = {
            "base_url": "https://api.example.com",
            "auth_type": "api_key",
            "api_key_header": "X-API-Key",
            "token": "my_key",
        }
        mock_get.return_value = mock_response([])
        conn = RESTConnector(config)
        conn.query("data")
        headers = mock_get.call_args[1]["headers"]
        assert headers["X-API-Key"] == "my_key"

    @patch("app.connectors.rest_connector.httpx.get")
    def test_test_connection(self, mock_get, rest_config):
        mock_get.return_value = mock_response({"status": "ok"})
        conn = RESTConnector(rest_config)
        assert conn.test_connection() is True

    @patch("app.connectors.rest_connector.httpx.get")
    def test_test_connection_failure(self, mock_get, rest_config):
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        conn = RESTConnector(rest_config)
        assert conn.test_connection() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/test_connector_rest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.connectors.rest_connector'`

- [ ] **Step 3: Implement RESTConnector**

```python
# backend/app/connectors/rest_connector.py
from typing import Any
import httpx
from app.connectors.base import BaseConnector, ColumnDef


class RESTConnector(BaseConnector):
    def test_connection(self) -> bool:
        try:
            url = self.config["base_url"]
            headers = self._build_auth_headers()
            resp = httpx.get(url, headers=headers, timeout=10)
            return resp.status_code < 500
        except Exception:
            return False

    def discover_schema(self, source: str, properties: list[dict] | None = None) -> list[ColumnDef]:
        if not properties:
            return []
        return [
            ColumnDef(name=p.get("name", ""), type=p.get("type", "string"))
            for p in properties
        ]

    def query(self, source, columns=None, filters=None, limit=None):
        url = f"{self.config['base_url'].rstrip('/')}/{source}"
        headers = self._build_auth_headers()
        params = self._build_params(filters)

        resp = httpx.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        rows = self._extract_rows(data)

        if columns:
            rows = [{k: row.get(k) for k in columns} for row in rows]

        if limit:
            rows = rows[:limit]

        return rows

    def _build_auth_headers(self) -> dict[str, str]:
        auth_type = self.config.get("auth_type", "none")
        token = self.config.get("token", "")

        if auth_type == "bearer":
            return {"Authorization": f"Bearer {token}"}
        if auth_type == "api_key":
            header_name = self.config.get("api_key_header", "X-API-Key")
            return {header_name: token}
        if auth_type == "basic":
            import base64
            user = self.config.get("username", "")
            pwd = self.config.get("password", "")
            encoded = base64.b64encode(f"{user}:{pwd}".encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        return {}

    def _build_params(self, filters: list[dict] | None) -> dict[str, str]:
        if not filters:
            return {}
        return {
            f["field"]: f["value"]
            for f in filters
            if f.get("operator", "=") == "="
        }

    def _extract_rows(self, data: Any) -> list[dict]:
        response_path = self.config.get("response_path", "")
        if response_path:
            for key in response_path.split("."):
                if isinstance(data, dict):
                    data = data.get(key, [])
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "data" in data:
            return data["data"] if isinstance(data["data"], list) else [data["data"]]
        return [data] if isinstance(data, dict) else []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/test_connector_rest.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/connectors/rest_connector.py backend/tests/test_connector_rest.py
git commit -m "feat: add RESTConnector for generic REST API data sources"
```

---

## Task 6: Register all connectors + wire into OmahaService

**Files:**
- Modify: `backend/app/connectors/__init__.py`
- Modify: `backend/app/services/omaha.py`
- Test: Run existing test suite to verify no regressions

- [ ] **Step 1: Update connectors __init__.py with auto-registration**

```python
# backend/app/connectors/__init__.py
from .registry import register, get_connector
from .sql_connector import SQLConnector
from .tushare_connector import TushareConnector
from .csv_connector import CSVConnector
from .rest_connector import RESTConnector

register("postgresql", SQLConnector)
register("mysql", SQLConnector)
register("sqlite", SQLConnector)
register("tushare", TushareConnector)
register("csv", CSVConnector)
register("excel", CSVConnector)
register("rest_api", RESTConnector)

__all__ = ["get_connector", "SQLConnector", "TushareConnector", "CSVConnector", "RESTConnector"]
```

- [ ] **Step 2: Refactor OmahaService.query_objects() to use connectors**

In `backend/app/services/omaha.py`, replace the data source dispatch logic in `query_objects()` (approximately lines 228-285). The method currently branches on `ds_type` to call `_query_tushare()` or build SQL. Replace with:

```python
# In query_objects(), replace the dispatch block with:
from app.connectors import get_connector

# ... after getting ds_config and obj_def ...
ds_type = ds_config.get("type", "")
connection_config = ds_config.get("connection", {})

# For SQL-based types, pass the type through so SQLConnector knows the dialect
if ds_type in ("sqlite", "mysql", "postgresql"):
    connector_config = {"type": ds_type, **connection_config}
else:
    connector_config = connection_config

connector = get_connector(ds_type, connector_config)
try:
    # Tushare still needs special handling for semantic formatting and computed properties
    # Keep _query_tushare() for now, but route through connector for basic queries
    if ds_type == "tushare":
        # Preserve existing Tushare behavior (semantic types, computed properties, technical indicators)
        return self._query_tushare(ds_config, obj_def, selected_columns, filters, limit)

    # SQL-based sources use SemanticQueryBuilder for advanced features (JOINs, computed properties)
    # Fall through to existing SQL path
    # ... existing SQL query building code ...
finally:
    connector.close()
```

Note: The full OmahaService refactor to eliminate `_query_tushare()` and `_execute_query()` is a larger change. For Phase 1, we wire up the connector registry and use it for new connector types (CSV, REST). Existing Tushare and SQL paths continue to work through their current code paths. The connectors are available for direct use by the new datasource API endpoints (Task 7).

- [ ] **Step 3: Run full test suite to verify no regressions**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/ --tb=short -q`
Expected: All existing tests still pass (198 passed)

- [ ] **Step 4: Commit**

```bash
git add backend/app/connectors/__init__.py backend/app/services/omaha.py
git commit -m "feat: register all connectors and wire into OmahaService"
```

---

## Task 7: Datasource API endpoints

**Files:**
- Create: `backend/app/api/datasources.py`
- Modify: `backend/app/main.py` — add router
- Test: `backend/tests/test_api_datasources.py`

- [ ] **Step 1: Write failing tests for datasource API**

```python
# backend/tests/test_api_datasources.py
import os
import csv
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test_datasources.db"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


client = TestClient(app)
state = {}

SAMPLE_CONFIG = """
datasources:
  - id: test_sqlite
    type: sqlite
    connection:
      database: ./test.db
ontology:
  objects:
    - name: Product
      datasource: test_sqlite
      table: products
      primary_key: id
      properties:
        - name: id
          column: id
          type: integer
"""


def _auth_headers():
    if "token" not in state:
        client.post("/api/v1/auth/register", json={
            "username": "dstest", "email": "dstest@test.com", "password": "testpass123"
        })
        resp = client.post("/api/v1/auth/login", json={
            "username": "dstest", "password": "testpass123"
        })
        state["token"] = resp.json()["access_token"]
        proj = client.post("/api/v1/projects/", json={
            "name": "DS Test", "omaha_config": SAMPLE_CONFIG
        }, headers={"Authorization": f"Bearer {state['token']}"}).json()
        state["project_id"] = proj["id"]
    return {"Authorization": f"Bearer {state['token']}"}


class TestDatasourceList:
    def test_list_datasources(self):
        h = _auth_headers()
        pid = state["project_id"]
        resp = client.get(f"/api/v1/datasources/{pid}/list", headers=h)
        assert resp.status_code == 200
        ds = resp.json()["datasources"]
        assert len(ds) >= 1
        assert ds[0]["id"] == "test_sqlite"
        assert ds[0]["type"] == "sqlite"


class TestDatasourceTest:
    def test_test_connection_sqlite(self):
        h = _auth_headers()
        pid = state["project_id"]
        resp = client.post(f"/api/v1/datasources/{pid}/test", json={
            "type": "sqlite",
            "connection": {"database": "./test.db"}
        }, headers=h)
        # May fail if test.db doesn't exist, but endpoint should respond
        assert resp.status_code == 200
        assert "connected" in resp.json()


class TestDatasourceUpload:
    def test_upload_csv(self, tmp_path):
        h = _auth_headers()
        pid = state["project_id"]
        csv_path = str(tmp_path / "test.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "value"])
            writer.writerow(["1", "A", "100"])
            writer.writerow(["2", "B", "200"])

        with open(csv_path, "rb") as f:
            resp = client.post(
                f"/api/v1/datasources/{pid}/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"table_name": "uploaded_test"},
                headers=h,
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["columns"]) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/test_api_datasources.py -v`
Expected: FAIL — 404 (routes not registered)

- [ ] **Step 3: Implement datasource API endpoints**

```python
# backend/app/api/datasources.py
import os
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.project import Project
from app.services.omaha import omaha_service
from app.connectors import get_connector
from app.connectors.csv_connector import CSVConnector

router = APIRouter(prefix="/datasources", tags=["datasources"])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


class TestConnectionRequest(BaseModel):
    type: str
    connection: dict


def _get_project(project_id: int, user: User, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/list")
def list_datasources(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_project(project_id, user, db)
    if not project.omaha_config:
        return {"datasources": []}

    config_yaml = project.omaha_config
    if isinstance(config_yaml, bytes):
        config_yaml = config_yaml.decode("utf-8")

    result = omaha_service.parse_config(config_yaml)
    if not result.get("valid"):
        return {"datasources": []}

    raw_ds = result["config"].get("datasources", [])
    return {
        "datasources": [
            {"id": ds.get("id"), "type": ds.get("type"), "name": ds.get("name", ds.get("id"))}
            for ds in raw_ds
        ]
    }


@router.post("/{project_id}/test")
def test_connection(
    project_id: int,
    req: TestConnectionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_project(project_id, user, db)
    try:
        config = req.connection
        if req.type in ("sqlite", "mysql", "postgresql"):
            config = {"type": req.type, **req.connection}
        connector = get_connector(req.type, config)
        connected = connector.test_connection()
        connector.close()
        return {"connected": connected}
    except ValueError as e:
        return {"connected": False, "error": str(e)}


@router.post("/{project_id}/upload")
async def upload_file(
    project_id: int,
    file: UploadFile = File(...),
    table_name: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_project(project_id, user, db)

    project_data_dir = os.path.join(DATA_DIR, str(project_id))
    uploads_dir = os.path.join(project_data_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    file_path = os.path.join(uploads_dir, file.filename or "upload.csv")
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    db_path = os.path.join(project_data_dir, "imported.db")
    connector = CSVConnector({"storage_path": uploads_dir, "database": db_path})
    columns = connector.ingest(file_path, table_name)

    return {
        "success": True,
        "table_name": table_name,
        "columns": [{"name": c.name, "type": c.type, "nullable": c.nullable} for c in columns],
        "file_path": file_path,
    }
```

- [ ] **Step 4: Register router in main.py**

In `backend/app/main.py`, add:

```python
from app.api.datasources import router as datasources_router
app.include_router(datasources_router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/test_api_datasources.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Run full test suite for regressions**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/ --tb=short -q`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/datasources.py backend/app/main.py backend/tests/test_api_datasources.py
git commit -m "feat: add datasource API endpoints (list, test, upload)"
```

---

## Task 8: Frontend — Datasource Manager Tab in Settings

**Files:**
- Create: `frontend/src/services/datasource.ts`
- Create: `frontend/src/pages/DatasourceManager.tsx`
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Create datasource API service**

```typescript
// frontend/src/services/datasource.ts
import api from './api';

export interface DatasourceInfo {
  id: string;
  type: string;
  name: string;
}

export interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
}

export const datasourceService = {
  list: async (projectId: number): Promise<DatasourceInfo[]> => {
    const res = await api.get(`/datasources/${projectId}/list`);
    return res.data.datasources;
  },

  testConnection: async (projectId: number, type: string, connection: Record<string, any>): Promise<{ connected: boolean; error?: string }> => {
    const res = await api.post(`/datasources/${projectId}/test`, { type, connection });
    return res.data;
  },

  upload: async (projectId: number, file: File, tableName: string): Promise<{ success: boolean; columns: ColumnInfo[] }> => {
    const form = new FormData();
    form.append('file', file);
    form.append('table_name', tableName);
    const res = await api.post(`/datasources/${projectId}/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
};
```

- [ ] **Step 2: Create DatasourceManager component**

```tsx
// frontend/src/pages/DatasourceManager.tsx
import React, { useState, useEffect, useRef } from 'react';
import { Upload, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { datasourceService, DatasourceInfo, ColumnInfo } from '@/services/datasource';

interface Props { projectId: number; }

const DatasourceManager: React.FC<Props> = ({ projectId }) => {
  const [datasources, setDatasources] = useState<DatasourceInfo[]>([]);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, boolean>>({});
  const [uploading, setUploading] = useState(false);
  const [tableName, setTableName] = useState('');
  const [uploadResult, setUploadResult] = useState<ColumnInfo[] | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { loadDatasources(); }, [projectId]);

  const loadDatasources = async () => {
    const ds = await datasourceService.list(projectId);
    setDatasources(ds);
  };

  const handleTest = async (ds: DatasourceInfo) => {
    setTesting(ds.id);
    const result = await datasourceService.testConnection(projectId, ds.type, {});
    setTestResults(prev => ({ ...prev, [ds.id]: result.connected }));
    setTesting(null);
  };

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file || !tableName) return;
    setUploading(true);
    try {
      const result = await datasourceService.upload(projectId, file, tableName);
      if (result.success) setUploadResult(result.columns);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="bg-surface border-white/10">
        <CardHeader><CardTitle className="text-white text-base">已配置的数据源</CardTitle></CardHeader>
        <CardContent>
          {datasources.length === 0 ? (
            <p className="text-slate-400 text-sm">暂无数据源，请在配置编辑中添加</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-white/10">
                  <TableHead className="text-slate-400">名称</TableHead>
                  <TableHead className="text-slate-400">类型</TableHead>
                  <TableHead className="text-slate-400">状态</TableHead>
                  <TableHead className="text-slate-400"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {datasources.map(ds => (
                  <TableRow key={ds.id} className="border-white/10">
                    <TableCell className="text-white">{ds.name}</TableCell>
                    <TableCell className="text-slate-400 font-mono text-xs">{ds.type}</TableCell>
                    <TableCell>
                      {ds.id in testResults ? (
                        testResults[ds.id]
                          ? <CheckCircle size={14} className="text-green-400" />
                          : <XCircle size={14} className="text-red-400" />
                      ) : <span className="text-slate-500 text-xs">未测试</span>}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" onClick={() => handleTest(ds)}
                        disabled={testing === ds.id} className="text-xs text-slate-400">
                        {testing === ds.id ? <Loader2 size={12} className="animate-spin" /> : '测试连接'}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card className="bg-surface border-white/10">
        <CardHeader><CardTitle className="text-white text-base">上传 CSV / Excel</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <Label className="text-slate-300">表名 *</Label>
            <Input value={tableName} onChange={e => setTableName(e.target.value)}
              placeholder="如: sales_data" className="bg-background border-white/10 text-white font-mono" />
          </div>
          <div className="space-y-1">
            <Label className="text-slate-300">文件</Label>
            <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls"
              className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:bg-primary/20 file:text-primary hover:file:bg-primary/30" />
          </div>
          <Button onClick={handleUpload} disabled={uploading || !tableName}
            className="bg-primary hover:bg-primary/90">
            <Upload size={14} className="mr-2" /> {uploading ? '上传中...' : '上传并导入'}
          </Button>

          {uploadResult && (
            <div className="mt-4">
              <p className="text-green-400 text-sm mb-2">导入成功，推断的 Schema：</p>
              <Table>
                <TableHeader>
                  <TableRow className="border-white/10">
                    <TableHead className="text-slate-400">列名</TableHead>
                    <TableHead className="text-slate-400">类型</TableHead>
                    <TableHead className="text-slate-400">可空</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {uploadResult.map(col => (
                    <TableRow key={col.name} className="border-white/10">
                      <TableCell className="text-white font-mono text-xs">{col.name}</TableCell>
                      <TableCell className="text-slate-400 text-xs">{col.type}</TableCell>
                      <TableCell className="text-slate-400 text-xs">{col.nullable ? '是' : '否'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default DatasourceManager;
```

- [ ] **Step 3: Add datasource tab to Settings.tsx**

In `frontend/src/pages/Settings.tsx`, add import and tab:

```tsx
import DatasourceManager from './DatasourceManager';

// In the TabsList, add after 项目管理:
<TabsTrigger value="datasources" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">
  数据源
</TabsTrigger>

// Add TabsContent after projects:
<TabsContent value="datasources" className="mt-4">
  {currentProject ? (
    <DatasourceManager projectId={currentProject.id} />
  ) : (
    <NoProjectHint />
  )}
</TabsContent>
```

- [ ] **Step 4: TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Build check**

Run: `cd frontend && npx vite build`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add frontend/src/services/datasource.ts frontend/src/pages/DatasourceManager.tsx frontend/src/pages/Settings.tsx
git commit -m "feat: add datasource manager UI in Settings"
```

---

## Task 9: Final integration test

**Files:**
- No new files — run all tests

- [ ] **Step 1: Run backend tests**

Run: `cd backend && ./venv311/bin/python3 -m pytest tests/ --tb=short -q`
Expected: All tests pass (existing + new connector + API tests)

- [ ] **Step 2: Run frontend checks**

Run: `cd frontend && npx tsc --noEmit && npx vite build`
Expected: Zero TS errors, build succeeds

- [ ] **Step 3: Manual smoke test**

Start backend and frontend, then verify:
1. Login → Settings → 数据源 tab shows configured datasources
2. Click "测试连接" on a datasource
3. Upload a CSV file → see inferred schema
4. Explorer still works for existing Tushare/SQL queries

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "test: verify connector framework integration"
```

