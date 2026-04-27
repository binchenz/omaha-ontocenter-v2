"""
Ontology SQLAlchemy models for semantic layer.
"""
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class OntologyObject(Base):
    __tablename__ = "ontology_objects"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    source_entity = Column(String, nullable=False)
    datasource_id = Column(String, nullable=False)
    datasource_type = Column(String, nullable=False)
    description = Column(Text)
    business_context = Column(Text)
    domain = Column(String(50), index=True)
    default_filters = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    properties = relationship("ObjectProperty", back_populates="object", cascade="all, delete-orphan")
    health_rules = relationship("HealthRule", back_populates="object", cascade="all, delete-orphan")
    business_goals = relationship("BusinessGoal", back_populates="object", cascade="all, delete-orphan")
    domain_knowledge_items = relationship("DomainKnowledge", back_populates="object", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tenant_object_name"),
        UniqueConstraint("tenant_id", "slug", name="uq_tenant_object_slug"),
    )


class ObjectProperty(Base):
    __tablename__ = "object_properties"

    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    semantic_type = Column(String(50))
    description = Column(Text)
    is_computed = Column(Boolean, default=False)
    expression = Column(Text)
    is_required = Column(Boolean, default=False)

    # Link type fields
    link_target_id = Column(Integer, ForeignKey("ontology_objects.id"), nullable=True, index=True)
    link_foreign_key = Column(String, nullable=True)
    link_target_key = Column(String, nullable=True, default="id")

    object = relationship("OntologyObject", back_populates="properties")
    link_target = relationship("OntologyObject", foreign_keys=[link_target_id])

    __table_args__ = (
        UniqueConstraint("object_id", "name", name="uq_object_property_name"),
        UniqueConstraint("object_id", "slug", name="uq_object_property_slug"),
    )


class OntologyRelationship(Base):
    __tablename__ = "ontology_relationships"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    from_object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False)
    to_object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(20), nullable=False)
    from_field = Column(String, nullable=False)
    to_field = Column(String, nullable=False)

    from_object = relationship("OntologyObject", foreign_keys=[from_object_id])
    to_object = relationship("OntologyObject", foreign_keys=[to_object_id])


class HealthRule(Base):
    __tablename__ = "health_rules"

    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    metric = Column(String, nullable=False)
    expression = Column(Text, nullable=False)
    warning_threshold = Column(String)
    critical_threshold = Column(String)
    advice = Column(Text)

    object = relationship("OntologyObject", back_populates="health_rules")


class BusinessGoal(Base):
    __tablename__ = "business_goals"

    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    metric = Column(String, nullable=False)
    target = Column(String, nullable=False)
    period = Column(String)

    object = relationship("OntologyObject", back_populates="business_goals")


class DomainKnowledge(Base):
    __tablename__ = "domain_knowledge"

    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("ontology_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    source = Column(String(20), default="template")

    object = relationship("OntologyObject", back_populates="domain_knowledge_items")
