from typing import Any
from pymongo import MongoClient
from app.connectors.base import BaseConnector, ColumnDef


class MongoDBConnector(BaseConnector):
    """Connector for MongoDB collections.

    Config keys:
      uri      — MongoDB connection URI (e.g. mongodb://localhost:27017)
      database — database name
    """

    def _client(self):
        return MongoClient(self.config["uri"], serverSelectionTimeoutMS=5000)

    def _collection(self, source: str):
        client = self._client()
        db = client[self.config["database"]]
        return client, db[source]

    def test_connection(self) -> bool:
        try:
            client = self._client()
            client.admin.command("ping")
            client.close()
            return True
        except Exception:
            return False

    def discover_schema(self, source: str) -> list[ColumnDef]:
        """Sample up to 100 documents to infer field names and types."""
        client, col = self._collection(source)
        try:
            docs = list(col.find({}, limit=100))
            if not docs:
                return []
            fields: dict[str, str] = {}
            for doc in docs:
                for key, val in doc.items():
                    if key == "_id":
                        continue
                    if key not in fields:
                        fields[key] = self._infer_type(val)
            return [ColumnDef(name=k, type=v) for k, v in fields.items()]
        finally:
            client.close()

    def query(self, source, columns=None, filters=None, limit=None):
        client, col = self._collection(source)
        try:
            mongo_filter = self._build_filter(filters or [])
            projection = None
            if columns:
                projection = {c: 1 for c in columns}
                projection["_id"] = 0

            cursor = col.find(mongo_filter, projection)
            if limit:
                cursor = cursor.limit(limit)

            rows = []
            for doc in cursor:
                doc.pop("_id", None)
                rows.append({k: self._serialize_value(v) for k, v in doc.items()})
            return rows
        finally:
            client.close()

    def _build_filter(self, filters: list[dict]) -> dict:
        mongo_filter: dict[str, Any] = {}
        op_map = {">": "$gt", "<": "$lt", ">=": "$gte", "<=": "$lte", "!=": "$ne"}
        for f in filters:
            field = f.get("field", "")
            op = f.get("operator", "=")
            value = f.get("value", "")
            if op == "=":
                mongo_filter[field] = value
            elif op in op_map:
                mongo_filter[field] = {op_map[op]: value}
            elif op == "IN":
                mongo_filter[field] = {"$in": [v.strip() for v in str(value).split(",")]}
        return mongo_filter

    @staticmethod
    def _infer_type(val: Any) -> str:
        if isinstance(val, bool):
            return "boolean"
        if isinstance(val, int):
            return "integer"
        if isinstance(val, float):
            return "decimal"
        return "string"
