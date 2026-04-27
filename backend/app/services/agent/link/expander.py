from typing import Any, Optional
from .resolver import LinkResolver, LinkDefinition


class LinkExpander:
    @staticmethod
    def expand_links(rows: list[dict[str, Any]], object_name: str, ontology: dict, ctx: Any) -> list[dict[str, Any]]:
        if not rows:
            return rows

        obj_data = next((o for o in ontology.get("objects", []) if o["name"] == object_name), None)
        if not obj_data:
            return rows

        link_fields = [p["slug"] for p in obj_data.get("properties", []) if p.get("type") == "link"]
        if not link_fields:
            return rows

        for link_field in link_fields:
            link_def = LinkResolver.resolve_link(object_name, link_field, ontology)
            if link_def:
                LinkExpander._expand_one_link(rows, link_def, ctx)

        return rows

    @staticmethod
    def _expand_one_link(rows: list[dict[str, Any]], link_def: LinkDefinition, ctx: Any) -> None:
        for row in rows:
            fk_value = row.get(link_def.foreign_key)
            if fk_value is not None:
                target_obj = LinkExpander._fetch_target_object(link_def, fk_value, ctx)
                row[link_def.link_field] = target_obj

    @staticmethod
    def _fetch_target_object(link_def: LinkDefinition, fk_value: Any, ctx: Any) -> Optional[dict[str, Any]]:
        result = ctx.omaha_service.query_objects(
            config_yaml=ctx.config_yaml,
            object_type=link_def.target_object,
            filters=[{"field": link_def.target_key, "operator": "=", "value": fk_value}],
            limit=1,
        )
        if result.get("success") and result.get("data"):
            return result["data"][0]
        return None
