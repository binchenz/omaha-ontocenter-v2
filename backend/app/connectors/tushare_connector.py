from typing import Any
import tushare as ts
import pandas as pd
from app.connectors.base import BaseConnector, ColumnDef

SUPPORTED_PARAMS = {
    "stock_basic": ["ts_code", "market", "list_status", "exchange"],
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
    def _pro(self):
        if not hasattr(self, "_pro_instance"):
            self._pro_instance = ts.pro_api(self.config["token"])
        return self._pro_instance

    def test_connection(self) -> bool:
        try:
            df = self._pro().stock_basic(ts_code="000001.SZ", fields="ts_code")
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
        pro = self._pro()
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
