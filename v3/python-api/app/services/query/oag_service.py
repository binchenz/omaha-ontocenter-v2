from app.services.query.duckdb_service import duckdb_service
from app.services.query.sql_safety import validate_identifier, validate_measure, escape_sql_value
from app.schemas.query import OAGQueryRequest, OAGQueryResponse, OAGMatch, OAGProperty, OAGContext


class OAGQueryService:
    async def execute(
        self, request: OAGQueryRequest, object_def: dict, properties_def: list[dict],
    ) -> OAGQueryResponse:
        view_name = object_def.get("table_name") or object_def["slug"]
        validate_identifier(view_name)
        delta_path = object_def.get("delta_path", "")
        if delta_path:
            duckdb_service.register_delta(view_name, delta_path)

        if request.operation == "count":
            total = duckdb_service.count(view_name)
            return OAGQueryResponse(object_type=object_def["name"], matched=[], context=OAGContext(total=total))
        elif request.operation == "aggregate":
            safe_measures = [validate_measure(m) for m in (request.measures or ["COUNT(*)"])]
            safe_groups = [validate_identifier(g) for g in (request.group_by or [])]
            rows = duckdb_service.aggregate(view_name, safe_measures, safe_groups)
            matched = [self._build_aggregate_match(row) for row in rows]
        else:
            rows = self._search(view_name, request.filters, request.limit)
            matched = [self._build_search_match(row, properties_def) for row in rows]

        return OAGQueryResponse(
            object_type=object_def["name"],
            matched=matched,
            context=OAGContext(total=len(matched)),
        )

    def _search(self, view: str, filters: dict | None, limit: int) -> list[dict]:
        sql = f'SELECT * FROM "{view}"'
        if filters:
            conditions = []
            for k, v in filters.items():
                safe_k = validate_identifier(k)
                safe_v = escape_sql_value(v)
                conditions.append(f'"{safe_k}" = \'{safe_v}\'')
            sql += " WHERE " + " AND ".join(conditions)
        sql += f" LIMIT {int(limit)}"
        return duckdb_service.query(sql)

    def _build_search_match(self, row: dict, properties_def: list[dict]) -> OAGMatch:
        row_id = str(row.get("id") or list(row.values())[0])
        props = {}
        for p in properties_def:
            col = p["source_column"] or p["name"]
            if col in row:
                props[p["name"]] = OAGProperty(
                    value=row[col],
                    semantic_type=p.get("semantic_type", "text"),
                    unit=p.get("unit"),
                )
        return OAGMatch(id=row_id, properties=props)

    def _build_aggregate_match(self, row: dict) -> OAGMatch:
        # Use first column as row ID
        keys = list(row.keys())
        row_id = str(row[keys[0]]) if keys else "0"
        props = {}
        for key in keys:
            val = row[key]
            sem_type = "number" if isinstance(val, (int, float)) else "text"
            props[key] = OAGProperty(value=val, semantic_type=sem_type)
        return OAGMatch(id=row_id, properties=props)


oag_service = OAGQueryService()
