import base64
from typing import Any, Optional, List, Dict, Union
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
