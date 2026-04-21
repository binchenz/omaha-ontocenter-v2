import os
import sqlite3
from typing import Any

import pymysql
import pymysql.cursors

from app.connectors.base import BaseConnector, ColumnDef


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
        if "INT" in t: return "integer"
        if "REAL" in t or "FLOAT" in t or "DOUBLE" in t: return "decimal"
        if "TEXT" in t or "CHAR" in t or "CLOB" in t: return "string"
        return "string"

    @staticmethod
    def _map_mysql_type(t: str) -> str:
        t = t.lower()
        if "int" in t: return "integer"
        if any(x in t for x in ("decimal", "float", "double", "numeric")): return "decimal"
        if "date" in t: return "date"
        if "time" in t: return "datetime"
        return "string"
