from typing import Any, Dict, List
from .resolver import LinkResolver


class PathNavigator:
    @staticmethod
    def navigate(params: Dict[str, Any], ontology: dict, ctx: Any) -> Dict[str, Any]:
        start_object = params["start_object"]
        path = params["path"]
        path_filters = params.get("path_filters", [])
        fields = params.get("fields", [])

        rows = PathNavigator._query(ctx, start_object, params.get("start_filters", {}))
        if not rows:
            return {"success": True, "data": []}

        current_object = start_object
        for i, link_field in enumerate(path):
            hop_filters = path_filters[i] if i < len(path_filters) else {}
            current_object, rows = PathNavigator._navigate_one_hop(
                rows, current_object, link_field, hop_filters, ontology, ctx
            )
            if not rows:
                return {"success": True, "data": []}

        if fields:
            rows = [{k: row[k] for k in fields if k in row} for row in rows]

        return {"success": True, "data": rows}

    @staticmethod
    def _query(ctx: Any, object_name: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run a single query through OmahaService and unwrap the result envelope."""
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
        link_def = LinkResolver.resolve_link(source_object, link_field, ontology)
        if not link_def:
            return None, []

        target_ids = [row[link_def.target_key] for row in rows if link_def.target_key in row]
        if not target_ids:
            return None, []

        filters = {link_def.foreign_key: target_ids, **hop_filters}
        return link_def.target_object, PathNavigator._query(ctx, link_def.target_object, filters)
