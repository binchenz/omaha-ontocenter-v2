from sqlalchemy.orm import Session, selectinload, joinedload
from app.models.ontology import (
    OntologyObject,
    ObjectProperty,
    OntologyRelationship,
    HealthRule,
    BusinessGoal,
    DomainKnowledge,
)


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
                      domain: str = None, default_filters: list = None) -> OntologyObject:
        return self._persist(OntologyObject(
            tenant_id=tenant_id, name=name, source_entity=source_entity,
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
                     is_computed: bool = False, expression: str = None) -> ObjectProperty:
        return self._persist(ObjectProperty(
            object_id=object_id, name=name, data_type=data_type,
            semantic_type=semantic_type, description=description,
            is_computed=is_computed, expression=expression,
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

    def get_full_ontology(self, tenant_id: int) -> dict:
        objects = (
            self.db.query(OntologyObject)
            .filter(OntologyObject.tenant_id == tenant_id)
            .options(
                selectinload(OntologyObject.properties),
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
                "source_entity": obj.source_entity,
                "datasource_id": obj.datasource_id,
                "description": obj.description,
                "business_context": obj.business_context,
                "domain": obj.domain,
                "properties": [
                    {"name": p.name, "type": p.data_type, "semantic_type": p.semantic_type,
                     "description": p.description, "is_computed": p.is_computed}
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
