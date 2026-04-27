from typing import Any, Dict, List, Optional
from .resolver import LinkResolver


class PathNavigator:
    @staticmethod
    def navigate(params: Dict[str, Any], ontology: dict, ctx: Any) -> Dict[str, Any]:
        start_object = params["start_object"]
        start_filters = params.get("start_filters", {})
        path = params["path"]
        fields = params.get("fields", [])
        path_filters = params.get("path_filters", [])

        start_rows = PathNavigator._query_start(start_object, start_filters, ctx)
        if not start_rows:
            return {"success": True, "data": []}

        current_rows = start_rows
        current_object = start_object

        for i, link_field in enumerate(path):
            hop_filters = path_filters[i] if i < len(path_filters) else {}
            link_target, current_rows = PathNavigator._navigate_one_hop(
                current_rows, current_object, link_field, hop_filters, ontology, ctx
            )
            if not current_rows:
                return {"success": True, "data": []}
            current_object = link_target

        if fields:
            current_rows = PathNavigator._select_fields(current_rows, fields)

        return {"success": True, "data": current_rows}

    @staticmethod
    def _query_start(object_name: str, filters: Dict[str, Any], ctx: Any) -> List[Dict[str, Any]]:
        result = ctx.omaha_service.query_objects(
            config_yaml=ctx.config_yaml,
            object_name=object_name,
            filters=filters,
        )
        return result.get("data", []) if result.get("success") else []

    @staticmethod
    def _navigate_one_hop(
        rows: List[Dict[str, Any]],
        source_object: str,
        link_field: str,
        hop_filters: Dict[str, Any],
        ontology: dict,
        ctx: Any,
    ):
        for obj in ontology.get("objects", []):
            link_prop = next((p for p in obj.get("properties", [])
                            if p["slug"] == link_field and p.get("type") == "link"
                            and p.get("link_target") == source_object), None)
            if link_prop:
                target_ids = [row["id"] for row in rows if "id" in row]
                if not target_ids:
                    return None, []

                foreign_key = link_prop.get("link_foreign_key")
                filters = {foreign_key: target_ids}
                filters.update(hop_filters)

                result = ctx.omaha_service.query_objects(
                    config_yaml=ctx.config_yaml,
                    object_name=obj["name"],
                    filters=filters,
                )
                data = result.get("data", []) if result.get("success") else []
                return obj["name"], data

        return None, []

    @staticmethod
    def _select_fields(rows: List[Dict[str, Any]], fields: List[str]) -> List[Dict[str, Any]]:
        return [{k: row[k] for k in fields if k in row} for row in rows]
