from __future__ import annotations
from typing import Optional, List, Dict, Union

from sqlalchemy.orm import Session, selectinload, joinedload
from app.models.ontology.ontology import (
    OntologyObject,
    ObjectProperty,
    OntologyRelationship,
    HealthRule,
    BusinessGoal,
    DomainKnowledge,
)
from app.services.ontology.slug import slugify_name, ensure_unique_slug


class OntologyStore:
    def __init__(self, db: Session):
        self.db = db

    def _persist(self, obj):
        self.db.add(obj)
        self.db.flush()
        self.db.refresh(obj)
        return obj

    def create_object(self, tenant_id: int, name: str, source_entity: str,
                      datasource_id: str, datasource_type: str,
                      description: str = None, business_context: str = None,
                      domain: str = None, default_filters: list = None,
                      slug: str = None) -> OntologyObject:
        # Always generate slug from name to ensure validity
        base_slug = slugify_name(name)
        slug = ensure_unique_slug(self.db, base_slug, "ontology_objects", "slug",
                                  tenant_id=tenant_id)
        return self._persist(OntologyObject(
            tenant_id=tenant_id, name=name, slug=slug, source_entity=source_entity,
            datasource_id=datasource_id, datasource_type=datasource_type,
            description=description, business_context=business_context,
            domain=domain, default_filters=default_filters or [],
        ))

    def get_object(self, tenant_id: int, name: str) -> OntologyObject | None:
        return (
            self.db.query(OntologyObject)
            .filter(OntologyObject.tenant_id == tenant_id, OntologyObject.name == name)
            .first()
        )

    def list_objects(self, tenant_id: int) -> list[OntologyObject]:
        return (
            self.db.query(OntologyObject)
            .filter(OntologyObject.tenant_id == tenant_id)
            .all()
        )

    def delete_object(self, tenant_id: int, name: str) -> bool:
        obj = self.get_object(tenant_id, name)
        if not obj:
            return False
        self.db.delete(obj)
        self.db.flush()
        return True

    def add_property(self, object_id: int, name: str, data_type: str,
                     semantic_type: str = None, description: str = None,
                     is_computed: bool = False, expression: str = None,
                     slug: str = None, link_target: str = None,
                     link_foreign_key: str = None, link_target_key: str = "id") -> ObjectProperty:
        if data_type == "link":
            if not link_target:
                raise ValueError("Link type requires link_target")
            if not link_foreign_key:
                raise ValueError("Link type requires link_foreign_key")

            obj = self.db.query(OntologyObject).filter(
                OntologyObject.id == object_id
            ).first()
            if not obj:
                raise ValueError(f"Object with id {object_id} not found")

            target_obj = self.db.query(OntologyObject).filter(
                OntologyObject.tenant_id == obj.tenant_id,
                OntologyObject.name == link_target
            ).first()
            if not target_obj:
                raise ValueError(f"Target object '{link_target}' not found")

            link_target_id = target_obj.id
        else:
            link_target_id = None
            link_foreign_key = None
            link_target_key = None

        # Always generate slug from name to ensure validity
        base_slug = slugify_name(name)
        slug = ensure_unique_slug(self.db, base_slug, "object_properties", "slug",
                                  object_id=object_id)
        return self._persist(ObjectProperty(
            object_id=object_id, name=name, slug=slug, data_type=data_type,
            semantic_type=semantic_type, description=description,
            is_computed=is_computed, expression=expression,
            link_target_id=link_target_id, link_foreign_key=link_foreign_key,
            link_target_key=link_target_key,
        ))

    def add_health_rule(self, object_id: int, metric: str, expression: str,
                        warning_threshold: str = None, critical_threshold: str = None,
                        advice: str = None) -> HealthRule:
        return self._persist(HealthRule(
            object_id=object_id, metric=metric, expression=expression,
            warning_threshold=warning_threshold, critical_threshold=critical_threshold,
            advice=advice,
        ))

    def add_relationship(self, tenant_id: int, name: str, from_object_id: int,
                         to_object_id: int, relationship_type: str,
                         from_field: str, to_field: str,
                         description: str = None) -> OntologyRelationship:
        return self._persist(OntologyRelationship(
            tenant_id=tenant_id, name=name, description=description,
            from_object_id=from_object_id, to_object_id=to_object_id,
            relationship_type=relationship_type,
            from_field=from_field, to_field=to_field,
        ))

    def add_business_goal(self, object_id: int, name: str, metric: str,
                          target: str, period: str = None) -> BusinessGoal:
        return self._persist(BusinessGoal(
            object_id=object_id, name=name, metric=metric,
            target=target, period=period,
        ))

    def add_domain_knowledge(self, object_id: int, content: str,
                             source: str = "template") -> DomainKnowledge:
        return self._persist(DomainKnowledge(
            object_id=object_id, content=content, source=source,
        ))

    def rename_object(self, tenant_id: int, old_name: str, new_name: str) -> bool:
        obj = self.get_object(tenant_id, old_name)
        if obj is None:
            return False
        obj.name = new_name
        base_slug = slugify_name(new_name)
        obj.slug = ensure_unique_slug(self.db, base_slug, "ontology_objects", "slug",
                                      exclude_id=obj.id, tenant_id=tenant_id)
        self.db.flush()
        return True

    def update_object_description(self, tenant_id: int, name: str, description: str) -> bool:
        obj = self.get_object(tenant_id, name)
        if obj is None:
            return False
        obj.description = description
        self.db.flush()
        return True

    def rename_property(self, object_id: int, old_name: str, new_name: str) -> bool:
        prop = self.db.query(ObjectProperty).filter(
            ObjectProperty.object_id == object_id,
            ObjectProperty.name == old_name,
        ).first()
        if prop is None:
            return False
        prop.name = new_name
        base_slug = slugify_name(new_name)
        prop.slug = ensure_unique_slug(self.db, base_slug, "object_properties", "slug",
                                       exclude_id=prop.id, object_id=object_id)
        self.db.flush()
        return True

    def update_property_semantic_type(self, object_id: int, name: str, semantic_type: Optional[str]) -> bool:
        prop = self.db.query(ObjectProperty).filter(
            ObjectProperty.object_id == object_id,
            ObjectProperty.name == name,
        ).first()
        if prop is None:
            return False
        prop.semantic_type = semantic_type
        self.db.flush()
        return True

    def update_property_description(self, object_id: int, name: str, description: str) -> bool:
        prop = self.db.query(ObjectProperty).filter(
            ObjectProperty.object_id == object_id,
            ObjectProperty.name == name,
        ).first()
        if prop is None:
            return False
        prop.description = description
        self.db.flush()
        return True

    def remove_property(self, object_id: int, name: str) -> bool:
        prop = self.db.query(ObjectProperty).filter(
            ObjectProperty.object_id == object_id,
            ObjectProperty.name == name,
        ).first()
        if prop is None:
            return False
        self.db.delete(prop)
        self.db.flush()
        return True

    def remove_relationship(self, tenant_id: int, name: str) -> bool:
        rel = self.db.query(OntologyRelationship).filter(
            OntologyRelationship.tenant_id == tenant_id,
            OntologyRelationship.name == name,
        ).first()
        if rel is None:
            return False
        self.db.delete(rel)
        self.db.flush()
        return True

    def get_full_ontology(self, tenant_id: int) -> dict:
        objects = (
            self.db.query(OntologyObject)
            .filter(OntologyObject.tenant_id == tenant_id)
            .options(
                selectinload(OntologyObject.properties).selectinload(ObjectProperty.link_target),
                selectinload(OntologyObject.health_rules),
                selectinload(OntologyObject.business_goals),
                selectinload(OntologyObject.domain_knowledge_items),
            )
            .all()
        )
        result = []
        for obj in objects:
            result.append({
                "name": obj.name,
                "slug": obj.slug,
                "source_entity": obj.source_entity,
                "datasource_id": obj.datasource_id,
                "datasource_type": obj.datasource_type,
                "description": obj.description,
                "business_context": obj.business_context,
                "domain": obj.domain,
                "properties": [
                    self._serialize_property(p)
                    for p in obj.properties
                ],
                "health_rules": [
                    {"metric": r.metric, "expression": r.expression,
                     "warning": r.warning_threshold, "critical": r.critical_threshold,
                     "advice": r.advice}
                    for r in obj.health_rules
                ],
                "goals": [
                    {"name": g.name, "metric": g.metric, "target": g.target}
                    for g in obj.business_goals
                ],
                "knowledge": [dk.content for dk in obj.domain_knowledge_items],
            })
        rels = (
            self.db.query(OntologyRelationship)
            .filter(OntologyRelationship.tenant_id == tenant_id)
            .options(
                joinedload(OntologyRelationship.from_object),
                joinedload(OntologyRelationship.to_object),
            )
            .all()
        )
        relationships = [
            {"name": r.name, "from": r.from_object.name, "to": r.to_object.name,
             "type": r.relationship_type, "from_field": r.from_field, "to_field": r.to_field}
            for r in rels
        ]
        return {"objects": result, "relationships": relationships}

    def _serialize_property(self, prop: ObjectProperty) -> dict:
        """序列化属性（包含Link信息）"""
        data = {
            "name": prop.name,
            "slug": prop.slug,
            "type": prop.data_type,
            "semantic_type": prop.semantic_type,
            "description": prop.description,
            "is_computed": prop.is_computed,
        }

        # 如果是Link类型，添加Link信息
        if prop.data_type == "link" and prop.link_target:
            data["link"] = {
                "target": prop.link_target.name,
                "target_slug": prop.link_target.slug,
                "foreign_key": prop.link_foreign_key,
                "target_key": prop.link_target_key or "id",
            }

        return data

