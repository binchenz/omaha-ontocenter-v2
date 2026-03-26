"""
Omaha Core integration service - Simplified for Phase 1.
"""
from typing import Dict, Any, List, Optional, Tuple
import yaml
import sqlite3
import pymysql
import os
import re
import tushare as ts
import pandas as pd

from app.services.semantic import semantic_service
from app.services.query_builder import SemanticQueryBuilder


def _find_by_name(items: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """Find an item in a list of dicts by its 'name' key."""
    return next((item for item in items if item.get("name") == name), None)


def _find_by_id(items: List[Dict[str, Any]], item_id: str) -> Optional[Dict[str, Any]]:
    """Find an item in a list of dicts by its 'id' key."""
    return next((item for item in items if item.get("id") == item_id), None)


class OmahaService:
    """Service for integrating with Omaha Core."""

    def parse_config(self, config_yaml: str) -> Dict[str, Any]:
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
        self, config_yaml: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Parse config and return (config_dict, ontology_dict, error_response).

        Error is None on success.
        """
        result = self.parse_config(config_yaml)
        if not result["valid"]:
            return None, None, result
        config = result["config"]
        return config, config.get("ontology", {}), None

    def _find_object(
        self, config_yaml: str, object_type: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Parse config and find object definition.

        Returns (config, ontology, obj_def, error_response).
        """
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

    def build_ontology(self, config_yaml: str) -> Dict[str, Any]:
        """Build ontology from configuration."""
        try:
            _, ontology, err = self._parse_ontology(config_yaml)
            if err:
                return err
            return {
                "valid": True,
                "ontology": {
                    "objects": ontology.get("objects", {}),
                    "relationships": ontology.get("relationships", []),
                },
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
        self, config_yaml: str, object_type: str
    ) -> Dict[str, Any]:
        """Get schema (columns) for an object type, enriched with semantic metadata."""
        try:
            result = semantic_service.get_schema_with_semantics(config_yaml, object_type)
            if result.get("success"):
                return result
            # Fallback to basic schema
            _, _, obj_def, err = self._find_object(config_yaml, object_type)
            if err:
                return err
            columns = [
                {
                    "name": prop.get("column") or prop.get("name"),
                    "type": prop.get("type", "string"),
                    "description": prop.get("description", ""),
                }
                for prop in obj_def.get("properties", [])
            ]
            return {"success": True, "columns": columns}
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
        config_yaml: str,
        object_type: str,
        selected_columns: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        joins: Optional[List[Dict[str, Any]]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Query objects using Omaha Core."""
        try:
            config, ontology, obj_def, err = self._find_object(config_yaml, object_type)
            if err:
                return err

            datasource_id = obj_def.get("datasource")
            ds_config = _find_by_id(config.get("datasources", []), datasource_id)
            if not ds_config:
                return {"success": False, "error": f"Datasource '{datasource_id}' not found"}

            ds_type = ds_config.get("type")
            if ds_type not in ("sqlite", "mysql", "tushare"):
                return {"success": False, "error": f"Unsupported datasource type: {ds_type}"}

            # Handle Tushare datasource separately
            if ds_type == "tushare":
                # Check for computed technical indicators
                if obj_def.get("api_name") == "computed_technical":
                    return self._compute_technical_indicators(ds_config, obj_def, filters, selected_columns, limit)
                return self._query_tushare(ds_config, obj_def, selected_columns, filters, limit)

            # Check if object uses custom query instead of table
            custom_query = obj_def.get("query")
            if custom_query:
                # Object uses custom query (e.g., Category, City, Platform)
                query, params = self._build_query_from_custom(
                    custom_query, object_type, selected_columns, filters, limit, ds_type
                )
            else:
                # Use SemanticQueryBuilder for table-based objects
                try:
                    builder = SemanticQueryBuilder(config_yaml, object_type)
                    query, params = builder.build(selected_columns, filters, joins, limit, ds_type)
                except ValueError:
                    # Fallback to original method if semantic parsing fails
                    objects = ontology.get("objects", [])
                    relationships = ontology.get("relationships", [])
                    table_name = obj_def.get("table")
                    query, params = self._build_select_query(
                        table_name, object_type, selected_columns, filters,
                        joins, relationships, objects, limit, ds_type,
                    )

            data = self._execute_query(ds_config, ds_type, query, params)

            return {"success": True, "data": data, "count": len(data), "sql": query}
        except Exception as e:
            return {"success": False, "error": str(e)}

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
            api_name = obj_def.get("api_name")
            if not api_name:
                return {"success": False, "error": "Object must have 'api_name' field for Tushare datasource"}

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
            }

            api_supported = supported_params.get(api_name, [])

            # Build API parameters and client-side filters
            api_params = {}
            client_filters = []

            # Apply default_filters first
            default_filters = obj_def.get("default_filters", [])
            if default_filters:
                for f in default_filters:
                    field = f.get("field")
                    value = f.get("value")
                    if field and value:
                        if field in api_supported:
                            api_params[field] = value
                        else:
                            client_filters.append({"field": field, "value": value})

            # Apply user-provided filters (can override defaults)
            if filters:
                for f in filters:
                    field = f.get("field")
                    value = f.get("value")
                    operator = f.get("operator", "=")
                    if field and value:
                        if field in api_supported:
                            api_params[field] = value
                        else:
                            # Store for client-side filtering
                            client_filters.append({"field": field, "value": value, "operator": operator})

            # Add limit parameter (will be applied after client-side filtering)
            # Request more data if we need to filter client-side
            api_limit = limit * 10 if client_filters else limit
            if api_limit:
                api_params["limit"] = api_limit

            # Call Tushare API
            df = getattr(pro, api_name)(**api_params)

            # Convert DataFrame to list of dicts
            if df is None or df.empty:
                return {"success": True, "data": [], "count": 0}

            # Apply client-side filters
            if client_filters:
                for f in client_filters:
                    field = f["field"]
                    value = f["value"]
                    operator = f.get("operator", "=")

                    if field in df.columns:
                        if operator == "=" or operator == "==":
                            df = df[df[field] == value]
                        elif operator == "!=":
                            df = df[df[field] != value]
                        elif operator == ">":
                            df = df[df[field] > value]
                        elif operator == ">=":
                            df = df[df[field] >= value]
                        elif operator == "<":
                            df = df[df[field] < value]
                        elif operator == "<=":
                            df = df[df[field] <= value]
                        elif operator == "in":
                            df = df[df[field].isin(value if isinstance(value, list) else [value])]

            # Apply limit after client-side filtering
            if limit and len(df) > limit:
                df = df.head(limit)

            # Filter columns if specified
            if selected_columns:
                available_cols = [col for col in selected_columns if col in df.columns]
                if available_cols:
                    df = df[available_cols]

            data = df.to_dict('records')
            return {"success": True, "data": data, "count": len(data)}

        except Exception as e:
            return {"success": False, "error": f"Tushare query failed: {str(e)}"}

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
            df = df.sort_values("trade_date", ascending=False).head(limit)

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
