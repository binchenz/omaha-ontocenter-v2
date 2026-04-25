"""
Omaha Core integration service - Simplified for Phase 1.
"""
from typing import Dict, Any, List, Optional, Tuple
import operator as op
import os
import re
import sqlite3

import pymysql
import pandas as pd
import tushare as ts
import yaml

from app.services.semantic import semantic_service
from app.services.query_builder import SemanticQueryBuilder
from app.services.computed_property_engine import ComputedPropertyEngine
from app.services.semantic_formatter import SemanticTypeFormatter


# Operator lookup for client-side DataFrame filtering
_DF_OPS = {
    "=": op.eq, "==": op.eq,
    "!=": op.ne,
    ">": op.gt, ">=": op.ge,
    "<": op.lt, "<=": op.le,
}


def _find_by_name(items: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """Find an item in a list of dicts by its 'name' key."""
    return next((item for item in items if item.get("name") == name), None)


def _find_by_id(items: List[Dict[str, Any]], item_id: str) -> Optional[Dict[str, Any]]:
    """Find an item in a list of dicts by its 'id' key."""
    return next((item for item in items if item.get("id") == item_id), None)


class OmahaService:
    """Service for integrating with Omaha Core."""

    def __init__(self, config_yaml: str = None):
        self.config_yaml = config_yaml

    def parse_config(self, config_yaml: str = None) -> Dict[str, Any]:
        config_yaml = config_yaml or self.config_yaml
        """Parse and validate Omaha configuration YAML."""
        try:
            # Substitute environment variables in YAML before parsing
            # Pattern: ${VAR_NAME} (uppercase only)
            def substitute_env_vars(text: str) -> str:
                """Replace ${VAR_NAME} patterns with environment variable values."""
                pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
                def replacer(match):
                    var_name = match.group(1)
                    return os.environ.get(var_name, match.group(0))
                return re.sub(pattern, replacer, text)

            config_yaml = substitute_env_vars(config_yaml)
            config_dict = yaml.safe_load(config_yaml)

            if not isinstance(config_dict, dict):
                return {
                    "valid": False,
                    "errors": ["Configuration must be a YAML dictionary"],
                    "warnings": [],
                }

            return {
                "valid": True,
                "errors": [],
                "warnings": [],
                "config": config_dict,
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
            }

    def _parse_ontology(
        self, config_yaml: str = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Parse config and return (config_dict, ontology_dict, error_response).

        Error is None on success.
        """
        config_yaml = config_yaml or self.config_yaml
        result = self.parse_config(config_yaml)
        if not result["valid"]:
            return None, None, result
        config = result["config"]
        return config, config.get("ontology", {}), None

    def _find_object(
        self, config_yaml: str = None, object_type: str = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Parse config and find object definition.

        Returns (config, ontology, obj_def, error_response).
        """
        config_yaml = config_yaml or self.config_yaml
        if not config_yaml:
            return None, None, None, {"success": False, "error": "No configuration provided"}
        if not object_type:
            return None, None, None, {"success": False, "error": "object_type required"}
        config, ontology, err = self._parse_ontology(config_yaml)
        if err:
            return None, None, None, {"success": False, "error": "Invalid configuration"}
        objects = ontology.get("objects", [])
        obj_def = _find_by_name(objects, object_type)
        if not obj_def:
            return None, None, None, {
                "success": False,
                "error": f"Object type '{object_type}' not found in ontology",
            }
        return config, ontology, obj_def, None

    def build_ontology(self, config_yaml: str = None) -> Dict[str, Any]:
        """Build ontology from configuration."""
        config_yaml = config_yaml or self.config_yaml
        try:
            _, ontology, err = self._parse_ontology(config_yaml)
            if err:
                return err
            objects = ontology.get("objects", [])
            relationships = ontology.get("relationships", [])
            return {
                "valid": True,
                "ontology": {
                    "objects": objects,
                    "relationships": relationships,
                },
                "objects": objects,
                "relationships": relationships,
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def get_relationships(
        self, config_yaml: str, object_type: str
    ) -> List[Dict[str, Any]]:
        """Get available relationships for an object type."""
        try:
            _, ontology, err = self._parse_ontology(config_yaml)
            if err:
                return []

            available = []
            for rel in ontology.get("relationships", []):
                if rel.get("from_object") == object_type:
                    available.append({
                        "name": rel.get("name"),
                        "description": rel.get("description", ""),
                        "from_object": rel.get("from_object"),
                        "to_object": rel.get("to_object"),
                        "type": rel.get("type"),
                        "join_condition": rel.get("join_condition"),
                        "direction": "forward",
                    })
                elif rel.get("to_object") == object_type:
                    join_cond = rel.get("join_condition", {})
                    available.append({
                        "name": rel.get("name"),
                        "description": rel.get("description", ""),
                        "from_object": rel.get("to_object"),
                        "to_object": rel.get("from_object"),
                        "type": rel.get("type"),
                        "join_condition": {
                            "from_field": join_cond.get("to_field"),
                            "to_field": join_cond.get("from_field"),
                        },
                        "direction": "reverse",
                    })
            return available
        except Exception:
            return []

    def get_object_schema(
        self, config_yaml: str = None, object_type: str = None
    ) -> Dict[str, Any]:
        """Get schema (columns) for an object type, enriched with semantic metadata."""
        if object_type is None and config_yaml is not None and self.config_yaml is not None:
            # Single positional argument is object_type
            object_type = config_yaml
            config_yaml = None
        config_yaml = config_yaml or self.config_yaml
        if not config_yaml or not object_type:
            return {"success": False, "error": "config_yaml and object_type are required"}
        try:
            result = semantic_service.get_schema_with_semantics(config_yaml, object_type)
            if result.get("success"):
                result["name"] = result.get("object_type", object_type)
                result["fields"] = result.get("columns", [])
                return result
            # Fallback to basic schema
            _, _, obj_def, err = self._find_object(config_yaml, object_type)
            if err:
                return err
            source_entity = obj_def.get("source_entity") or obj_def.get("api_name", "")
            fields = [
                {
                    "name": prop.get("column") or prop.get("name"),
                    "type": prop.get("type", "string"),
                    "description": prop.get("description", ""),
                }
                for prop in obj_def.get("properties", [])
            ]
            return {
                "success": True,
                "name": object_type,
                "object_type": object_type,
                "source_entity": source_entity,
                "fields": fields,
                "columns": fields,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_join_clause(
        self,
        joins: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        objects: List[Dict[str, Any]],
    ) -> str:
        """Build JOIN clause from join configurations."""
        if not joins:
            return ""

        join_clauses = []
        for join_config in joins:
            relationship = _find_by_name(relationships, join_config.get("relationship_name"))
            if not relationship:
                continue

            to_object = _find_by_name(objects, relationship.get("to_object"))
            if not to_object:
                continue

            to_table = to_object.get("table")
            join_condition = relationship.get("join_condition", {})
            from_field = join_condition.get("from_field")
            to_field = join_condition.get("to_field")

            if not all([to_table, from_field, to_field]):
                continue

            join_type = join_config.get("join_type", "LEFT").upper()
            from_obj = relationship.get("from_object")
            to_obj = relationship.get("to_object")
            join_clauses.append(
                f"{join_type} JOIN {to_table} AS {to_obj}"
                f" ON {from_obj}.{from_field} = {to_obj}.{to_field}"
            )

        return " ".join(join_clauses)

    def query_objects(
        self,
        config_yaml: str = None,
        object_type: str = None,
        selected_columns: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        joins: Optional[List[Dict[str, Any]]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Query objects using Omaha Core."""
        if object_type is None and config_yaml is not None and self.config_yaml is not None:
            # Single positional argument is object_type
            object_type = config_yaml
            config_yaml = None
        config_yaml = config_yaml or self.config_yaml
        if not config_yaml:
            return {"success": False, "error": "No configuration provided"}
        if not object_type:
            return {"success": False, "error": "object_type required"}
        try:
            config, ontology, obj_def, err = self._find_object(config_yaml, object_type)
            if err:
                return err

            datasource_id = obj_def.get("datasource")
            ds_config = _find_by_id(config.get("datasources", []), datasource_id)
            if not ds_config:
                return {"success": False, "error": f"Datasource '{datasource_id}' not found"}

            ds_type = ds_config.get("type", "")

            # Route by datasource type
            if ds_type == "tushare":
                source_entity = obj_def.get("source_entity") or obj_def.get("api_name", "")
                if source_entity == "computed_technical":
                    return self._compute_technical_indicators(ds_config, obj_def, filters, selected_columns, limit)
                return self._query_tushare(ds_config, obj_def, selected_columns, filters, limit)
            else:
                return self._query_connector(obj_def, ds_config, selected_columns, filters, limit)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _query_connector(self, obj_def, ds_config, selected_columns, filters, limit):
        from app.connectors.registry import get_connector
        source_entity = obj_def.get("source_entity") or obj_def.get("api_name", "")
        connector = get_connector(ds_config["type"], ds_config.get("connection", {}))
        try:
            raw_data = connector.query(
                source=source_entity,
                columns=selected_columns,
                filters=filters,
                limit=limit,
            )
            return {"success": True, "data": raw_data, "count": len(raw_data)}
        finally:
            connector.close()

    def _build_where_clause(
        self, filters: List[Dict[str, Any]], db_type: str
    ) -> Tuple[str, List[Any]]:
        """Build WHERE clause from filters."""
        conditions: List[str] = []
        params: List[Any] = []
        placeholder = "?" if db_type == "sqlite" else "%s"

        for f in filters:
            field = f.get("field")
            operator = f.get("operator", "=")
            value = f.get("value")

            op_upper = operator.upper()
            if op_upper == "IN":
                values = [v.strip() for v in str(value).split(",")]
                placeholders = ",".join([placeholder] * len(values))
                conditions.append(f"{field} IN ({placeholders})")
                params.extend(values)
            elif op_upper == "LIKE":
                conditions.append(f"{field} LIKE {placeholder}")
                params.append(f"%{value}%")
            else:
                conditions.append(f"{field} {operator} {placeholder}")
                params.append(value)

        return " AND ".join(conditions), params

    def _build_query_from_custom(
        self,
        custom_query: str,
        object_type: str,
        selected_columns: Optional[List[str]],
        filters: Optional[List[Dict[str, Any]]],
        limit: int,
        db_type: str,
    ) -> Tuple[str, List[Any]]:
        """Build query from custom SQL query definition.

        For objects that use 'query' field instead of 'table'.
        Wraps the custom query as a subquery and applies filters/limits.
        """
        params: List[Any] = []

        # Wrap custom query as subquery
        if selected_columns:
            columns_str = ", ".join(selected_columns)
        else:
            columns_str = "*"

        query = f"SELECT {columns_str} FROM ({custom_query.strip()}) AS {object_type}"

        # Apply filters if provided
        if filters:
            where_clause, params = self._build_where_clause(filters, db_type)
            if where_clause:
                query += f" WHERE {where_clause}"

        # Apply limit
        if limit is not None:
            query += f" LIMIT {limit}"

        return query, params

    def _build_select_query(
        self,
        table_name: str,
        object_type: str,
        selected_columns: Optional[List[str]],
        filters: Optional[List[Dict[str, Any]]],
        joins: Optional[List[Dict[str, Any]]],
        relationships: List[Dict[str, Any]],
        objects: List[Dict[str, Any]],
        limit: int,
        db_type: str,
    ) -> Tuple[str, List[Any]]:
        """Build a SELECT query string and parameter list."""
        columns_str = ", ".join(selected_columns) if selected_columns else "*"
        query = f"SELECT {columns_str} FROM {table_name} AS {object_type}"
        params: List[Any] = []

        if joins:
            join_clause = self._build_join_clause(joins, relationships, objects)
            if join_clause:
                query += f" {join_clause}"

        if filters:
            where_clause, params = self._build_where_clause(filters, db_type)
            if where_clause:
                query += f" WHERE {where_clause}"

        if limit is not None:
            query += f" LIMIT {limit}"
        return query, params

    def _connect_sqlite(self, ds_config: Dict[str, Any]) -> sqlite3.Connection:
        """Create a SQLite connection from datasource config."""
        db_path = ds_config.get("connection", {}).get("database")
        if not db_path:
            raise ValueError("Database path not specified")

        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)

        if not os.path.exists(db_path):
            raise ValueError(f"Database file not found: {db_path}")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _connect_mysql(self, ds_config: Dict[str, Any]) -> pymysql.connections.Connection:
        """Create a MySQL connection from datasource config."""
        connection_config = ds_config.get("connection", {})
        return pymysql.connect(
            host=connection_config.get("host"),
            port=connection_config.get("port", 3306),
            user=connection_config.get("user"),
            password=connection_config.get("password"),
            database=connection_config.get("database"),
            connect_timeout=10,
            charset="utf8mb4",
        )

    def _query_tushare(
        self,
        ds_config: Dict[str, Any],
        obj_def: Dict[str, Any],
        selected_columns: Optional[List[str]],
        filters: Optional[List[Dict[str, Any]]],
        limit: int,
    ) -> Dict[str, Any]:
        """Query Tushare Pro API."""
        try:
            # Get token from datasource config
            token = ds_config.get("connection", {}).get("token")
            if not token:
                return {"success": False, "error": "Tushare token not found in datasource config"}

            # Initialize Tushare Pro API
            pro = ts.pro_api(token)

            # Get API name and params from object definition
            api_name = obj_def.get("source_entity") or obj_def.get("api_name")
            if not api_name:
                return {"success": False, "error": "Object must have 'source_entity' or 'api_name' field for Tushare datasource"}

            # Define supported API parameters for each API
            # These are parameters that Tushare API accepts directly
            supported_params = {
                "stock_basic": ["ts_code", "name", "exchange", "market", "list_status", "is_hs"],
                "daily": ["ts_code", "trade_date", "start_date", "end_date"],
                "daily_basic": ["ts_code", "trade_date", "start_date", "end_date"],
                "fina_indicator": ["ts_code", "ann_date", "start_date", "end_date", "period"],
                "income": ["ts_code", "ann_date", "start_date", "end_date", "period", "report_type", "comp_type"],
                "balancesheet": ["ts_code", "ann_date", "start_date", "end_date", "period", "report_type", "comp_type"],
                "cashflow": ["ts_code", "ann_date", "start_date", "end_date", "period", "report_type", "comp_type"],
                "concept": ["src"],
                "concept_detail": ["id", "ts_code"],
            }

            api_supported = supported_params.get(api_name, [])

            # Combine default_filters and user filters, then split into
            # API-side params vs client-side filters
            all_filters = list(obj_def.get("default_filters", []))
            all_filters.extend(filters or [])

            api_params = {}
            client_filters = []
            for f in all_filters:
                field = f.get("field")
                value = f.get("value")
                if not (field and value):
                    continue
                if field in api_supported:
                    api_params[field] = value
                else:
                    client_filters.append({
                        "field": field,
                        "value": value,
                        "operator": f.get("operator", "="),
                    })

            # Request more data if we need to filter client-side
            if limit is not None:
                api_params["limit"] = limit * 10 if client_filters else limit

            # Call Tushare API
            df = getattr(pro, api_name)(**api_params)

            # Convert DataFrame to list of dicts
            if df is None or df.empty:
                return {"success": True, "data": [], "count": 0}

            # Apply client-side filters
            for f in client_filters:
                field = f["field"]
                value = f["value"]
                operator = f.get("operator", "=")

                if field not in df.columns:
                    continue

                if operator == "in":
                    df = df[df[field].isin(value if isinstance(value, list) else [value])]
                elif operator in _DF_OPS:
                    df = df[_DF_OPS[operator](df[field], value)]

            # Apply limit after client-side filtering
            if limit is not None and len(df) > limit:
                df = df.head(limit)

            # Apply computed properties if defined
            computed_props = obj_def.get('computed_properties', [])
            if computed_props and not df.empty:
                try:
                    engine = ComputedPropertyEngine()
                    df = engine.compute_properties(df, computed_props)
                except Exception as e:
                    return {"success": False, "error": f"Computed property error: {str(e)}"}

            # Filter columns if specified
            if selected_columns:
                available_cols = [col for col in selected_columns if col in df.columns]
                if available_cols:
                    df = df[available_cols]

            # Apply semantic type formatting
            data = self._format_data_with_semantic_types(df, obj_def)
            return {"success": True, "data": data, "count": len(data)}

        except Exception as e:
            return {"success": False, "error": f"Tushare query failed: {str(e)}"}

    def _format_data_with_semantic_types(
        self, df: pd.DataFrame, obj_def: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Format data with semantic types."""
        if df.empty:
            return []

        # Build semantic type map from both regular and computed properties
        all_props = obj_def.get('properties', []) + obj_def.get('computed_properties', [])
        semantic_type_map = {
            prop['name']: prop['semantic_type']
            for prop in all_props
            if 'semantic_type' in prop
        }

        data = df.to_dict('records')

        if semantic_type_map:
            formatter = SemanticTypeFormatter()
            for record in data:
                for field, semantic_type in semantic_type_map.items():
                    if field in record:
                        record[field] = formatter.format_value(
                            record[field], semantic_type
                        )

        return data

    def _compute_technical_indicators(
        self,
        ds_config: Dict[str, Any],
        obj_def: Dict[str, Any],
        filters: Optional[List[Dict[str, Any]]],
        selected_columns: Optional[List[str]],
        limit: int,
    ) -> Dict[str, Any]:
        """Compute technical indicators (MA, MACD, RSI, KDJ) from daily price data."""
        try:
            token = ds_config.get("connection", {}).get("token")
            if not token:
                return {"success": False, "error": "Tushare token not found"}

            # Extract ts_code from filters (required)
            ts_code = None
            for f in (filters or []):
                if f.get("field") == "ts_code":
                    ts_code = f.get("value")
                    break
            if not ts_code:
                return {"success": False, "error": "ts_code is required for TechnicalIndicator queries"}

            # Fetch enough daily data to compute indicators (need at least 60 days)
            pro = ts.pro_api(token)
            df = pro.daily(ts_code=ts_code, limit=120)
            if df is None or df.empty:
                return {"success": True, "data": [], "count": 0}

            # Sort ascending for calculation
            df = df.sort_values("trade_date").reset_index(drop=True)
            close = df["close"]

            # MA indicators
            df["ma5"] = close.rolling(5).mean().round(4)
            df["ma10"] = close.rolling(10).mean().round(4)
            df["ma20"] = close.rolling(20).mean().round(4)
            df["ma60"] = close.rolling(60).mean().round(4)

            # MACD (12, 26, 9)
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            df["macd_dif"] = (ema12 - ema26).round(4)
            df["macd_dea"] = df["macd_dif"].ewm(span=9, adjust=False).mean().round(4)
            df["macd_bar"] = ((df["macd_dif"] - df["macd_dea"]) * 2).round(4)

            # RSI (14)
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, float("nan"))
            df["rsi14"] = (100 - 100 / (1 + rs)).round(2)

            # KDJ (9, 3, 3)
            low_min = df["low"].rolling(9).min()
            high_max = df["high"].rolling(9).max()
            rsv = ((close - low_min) / (high_max - low_min).replace(0, float("nan")) * 100)
            df["kdj_k"] = rsv.ewm(com=2, adjust=False).mean().round(2)
            df["kdj_d"] = df["kdj_k"].ewm(com=2, adjust=False).mean().round(2)
            df["kdj_j"] = (3 * df["kdj_k"] - 2 * df["kdj_d"]).round(2)

            # Add signal columns
            df["ma_signal"] = "neutral"
            df.loc[df["ma5"] > df["ma20"], "ma_signal"] = "bullish"
            df.loc[df["ma5"] < df["ma20"], "ma_signal"] = "bearish"

            df["macd_signal"] = "neutral"
            df.loc[df["macd_bar"] > 0, "macd_signal"] = "bullish"
            df.loc[df["macd_bar"] < 0, "macd_signal"] = "bearish"

            df["rsi_signal"] = "neutral"
            df.loc[df["rsi14"] > 70, "rsi_signal"] = "overbought"
            df.loc[df["rsi14"] < 30, "rsi_signal"] = "oversold"

            # Sort descending (latest first) and limit
            df = df.sort_values("trade_date", ascending=False)
            if limit is not None:
                df = df.head(limit)

            # Filter columns if specified
            all_cols = ["ts_code", "trade_date", "close", "ma5", "ma10", "ma20", "ma60",
                       "macd_dif", "macd_dea", "macd_bar", "rsi14",
                       "kdj_k", "kdj_d", "kdj_j", "ma_signal", "macd_signal", "rsi_signal"]
            if selected_columns:
                cols = [c for c in selected_columns if c in df.columns]
                if cols:
                    df = df[cols]
            else:
                df = df[[c for c in all_cols if c in df.columns]]

            data = df.to_dict("records")
            return {"success": True, "data": data, "count": len(data)}

        except Exception as e:
            return {"success": False, "error": f"Technical indicator computation failed: {str(e)}"}

    def _execute_query(
        self, ds_config: Dict[str, Any], ds_type: str, query: str, params: List[Any]
    ) -> List[Dict[str, Any]]:
        """Execute a query against the appropriate database backend."""
        if ds_type == "sqlite":
            conn = self._connect_sqlite(ds_config)
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()

        conn = self._connect_mysql(ds_config)
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query, params)
            return [
                {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in row.items()}
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def analyze_pricing(
        self, config_yaml: str, object_type: str
    ) -> Dict[str, Any]:
        """Analyze pricing for objects."""
        return {
            "success": True,
            "metrics": {},
            "message": "Pricing analysis placeholder - to be implemented in Phase 2",
        }


omaha_service = OmahaService()
