from dataclasses import dataclass
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
    def resolve_link(object_name: str, link_field_slug: str, ontology: dict) -> LinkDefinition | None:
        obj_data = next((o for o in ontology.get("objects", []) if o["name"] == object_name), None)
        if not obj_data:
            return None

        prop = next((p for p in obj_data.get("properties", []) if p["slug"] == link_field_slug), None)
        if not prop or prop.get("type") != "link":
            return None

        target_name = prop.get("link_target")
        if not target_name:
            return None

        target_obj = next((o for o in ontology.get("objects", []) if o["name"] == target_name), None)
        if not target_obj:
            return None

        return LinkDefinition(
            source_object=object_name,
            source_slug=obj_data["slug"],
            link_field=link_field_slug,
            target_object=target_name,
            target_slug=target_obj["slug"],
            foreign_key=prop.get("link_foreign_key"),
            target_key=prop.get("link_target_key", "id"),
            datasource_type=obj_data["datasource_type"],
            datasource_id=obj_data["datasource_id"],
        )
