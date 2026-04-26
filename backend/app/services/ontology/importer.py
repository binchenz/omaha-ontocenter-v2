import yaml
from sqlalchemy.orm import Session
from app.services.ontology_store import OntologyStore


class OntologyImporter:
    def __init__(self, db: Session):
        self.db = db
        self.store = OntologyStore(db)

    def import_yaml(self, tenant_id: int, yaml_content: str) -> dict:
        if len(yaml_content) > 1_000_000:
            raise ValueError("YAML content exceeds 1MB limit")
        config = yaml.safe_load(yaml_content)
        if not isinstance(config, dict):
            raise ValueError("YAML must be a dictionary")
        return self.import_dict(tenant_id, config)

    def import_dict(self, tenant_id: int, config: dict) -> dict:
        ontology = config.get("ontology", {})
        datasources_list = config.get("datasources", [])
        if not isinstance(datasources_list, list):
            raise ValueError("datasources must be a list")
        datasources = {ds["id"]: ds for ds in datasources_list}

        objects_created = 0
        objects_updated = 0
        object_map = {}

        for obj_def in ontology.get("objects", []):
            ds_id = obj_def.get("datasource", "")
            ds_type = datasources.get(ds_id, {}).get("type", "unknown")
            source_entity = obj_def.get("source_entity") or obj_def.get("api_name", "")

            existing = self.store.get_object(tenant_id, obj_def["name"])
            if existing:
                self.store.delete_object(tenant_id, obj_def["name"])
                objects_updated += 1
            else:
                objects_created += 1

            obj = self.store.create_object(
                tenant_id=tenant_id,
                name=obj_def["name"],
                source_entity=source_entity,
                datasource_id=ds_id,
                datasource_type=ds_type,
                description=obj_def.get("description"),
                business_context=obj_def.get("business_context"),
                domain=obj_def.get("domain"),
                default_filters=obj_def.get("default_filters"),
            )
            object_map[obj_def["name"]] = obj
            if source_entity:
                object_map[source_entity] = obj

            for prop in obj_def.get("properties", []):
                self.store.add_property(
                    object_id=obj.id,
                    name=prop["name"],
                    data_type=prop.get("type", prop.get("data_type", "string")),
                    semantic_type=prop.get("semantic_type"),
                    description=prop.get("description"),
                )

            for cp in obj_def.get("computed_properties", []):
                self.store.add_property(
                    object_id=obj.id,
                    name=cp["name"],
                    data_type="float",
                    semantic_type=cp.get("semantic_type"),
                    description=cp.get("description"),
                    is_computed=True,
                    expression=cp.get("expression"),
                )

            for rule in obj_def.get("health_rules", []):
                self.store.add_health_rule(
                    object_id=obj.id,
                    metric=rule["metric"],
                    expression=rule["expression"],
                    warning_threshold=rule.get("warning"),
                    critical_threshold=rule.get("critical"),
                    advice=rule.get("advice"),
                )

            for goal in obj_def.get("goals", []):
                self.store.add_business_goal(
                    object_id=obj.id,
                    name=goal["name"],
                    metric=goal["metric"],
                    target=goal["target"],
                    period=goal.get("period"),
                )

            for dk in obj_def.get("domain_knowledge", []):
                self.store.add_domain_knowledge(object_id=obj.id, content=dk)

        relationships_created = 0
        for rel_def in ontology.get("relationships", []):
            from_obj = object_map.get(rel_def.get("from_object"))
            to_obj = object_map.get(rel_def.get("to_object"))
            if from_obj and to_obj:
                join = rel_def.get("join_condition", {})
                self.store.add_relationship(
                    tenant_id=tenant_id,
                    name=rel_def["name"],
                    from_object_id=from_obj.id,
                    to_object_id=to_obj.id,
                    relationship_type=rel_def.get("type", rel_def.get("relationship_type", "one_to_many")),
                    from_field=join.get("from_field", rel_def.get("from_field", "")),
                    to_field=join.get("to_field", rel_def.get("to_field", "")),
                    description=rel_def.get("description"),
                )
                relationships_created += 1

        self.db.commit()
        return {
            "objects_created": objects_created,
            "objects_updated": objects_updated,
            "relationships_created": relationships_created,
        }
