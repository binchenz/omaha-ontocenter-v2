from app.services.query.duckdb_service import duckdb_service


class LinkResolver:
    """Resolve forward/reverse links between ontology objects."""

    def __init__(self, ontology_config: dict):
        self.objects = {o["slug"]: o for o in ontology_config.get("objects", [])}
        self.links = ontology_config.get("links", [])

    async def resolve_forward(self, link_def: dict, source_ids: list[str]) -> list[dict]:
        """Resolve forward (FK) links: for each source_id, find target record."""
        target_obj = self.objects.get(link_def["to_object"])
        from_col = link_def.get("from_column", "")
        to_col = link_def.get("to_column", "id")

        if not target_obj:
            return []

        view = target_obj.get("table_name") or target_obj["slug"]
        ids_str = ", ".join(f"'{i}'" for i in source_ids)
        sql = f'SELECT * FROM "{view}" WHERE "{to_col}" IN ({ids_str})'
        return duckdb_service.query(sql)

    async def resolve_reverse(self, link_def: dict, source_ids: list[str]) -> list[dict]:
        """Resolve reverse links: find all records that point to source_ids."""
        from_obj = self.objects.get(link_def["from_object"])
        from_col = link_def.get("from_column", "")
        to_col = link_def.get("to_column", "id")

        if not from_obj:
            return []

        view = from_obj.get("table_name") or from_obj["slug"]
        ids_str = ", ".join(f"'{i}'" for i in source_ids)
        sql = f'SELECT * FROM "{view}" WHERE "{from_col}" IN ({ids_str})'
        return duckdb_service.query(sql)
