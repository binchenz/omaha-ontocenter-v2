from dataclasses import dataclass
from typing import Optional
from app.models.ontology.ontology import OntologyObject, ObjectProperty


@dataclass
class LinkDefinition:
    source_object: str
    source_slug: str
    link_field: str
    target_object: str
    target_slug: str
    foreign_key: str
    target_key: str
    datasource_type: str
    datasource_id: str


class LinkResolver:
    @staticmethod
    def resolve_link(object_name: str, link_field_slug: str, ontology: dict) -> Optional[LinkDefinition]:
        obj_data = next((o for o in ontology.get("objects", []) if o["name"] == object_name), None)
        if not obj_data:
            return None

        prop = next((p for p in obj_data.get("properties", []) if p["slug"] == link_field_slug), None)
        if not prop or prop.get("type") != "link":
            return None

        # Support both formats: nested "link" dict (new) and flat "link_target" (legacy)
        link_info = prop.get("link") or {}
        target_name = link_info.get("target") or prop.get("link_target")
        if not target_name:
            return None

        foreign_key = link_info.get("foreign_key") or prop.get("link_foreign_key")
        target_key = link_info.get("target_key") or prop.get("link_target_key") or "id"

        target_obj = next((o for o in ontology.get("objects", []) if o["name"] == target_name), None)
        if not target_obj:
            return None

        return LinkDefinition(
            source_object=object_name,
            source_slug=obj_data["slug"],
            link_field=link_field_slug,
            target_object=target_name,
            target_slug=target_obj["slug"],
            foreign_key=foreign_key,
            target_key=target_key,
            datasource_type=obj_data.get("datasource_type", ""),
            datasource_id=obj_data.get("datasource_id", ""),
        )
