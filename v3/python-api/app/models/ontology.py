from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class OntologyStatus(str, enum.Enum):
    draft = "draft"
    published = "published"


class Ontology(Base):
    __tablename__ = "ontologies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[OntologyStatus] = mapped_column(SQLEnum(OntologyStatus), default=OntologyStatus.draft)
    yaml_source: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    objects: Mapped[list["OntologyObject"]] = relationship(back_populates="ontology")
    links: Mapped[list["OntologyLink"]] = relationship(back_populates="ontology")
    functions: Mapped[list["OntologyFunction"]] = relationship(back_populates="ontology")


class OntologyObject(Base):
    __tablename__ = "ontology_objects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ontology_id: Mapped[str] = mapped_column(String, ForeignKey("ontologies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    datasource_id: Mapped[str] = mapped_column(String, default="")
    table_name: Mapped[str] = mapped_column(String, default="")

    ontology: Mapped["Ontology"] = relationship(back_populates="objects")
    properties: Mapped[list["OntologyProperty"]] = relationship(back_populates="object")


class OntologyProperty(Base):
    __tablename__ = "ontology_properties"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    object_id: Mapped[str] = mapped_column(String, ForeignKey("ontology_objects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    semantic_type: Mapped[str] = mapped_column(String, default="text")
    source_column: Mapped[str] = mapped_column(String, default="")
    is_computed: Mapped[bool] = mapped_column(default=False)
    function_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    unit: Mapped[str] = mapped_column(String, default="")

    object: Mapped["OntologyObject"] = relationship(back_populates="properties")


class OntologyLink(Base):
    __tablename__ = "ontology_links"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ontology_id: Mapped[str] = mapped_column(String, ForeignKey("ontologies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    from_object: Mapped[str] = mapped_column(String, nullable=False)
    to_object: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, default="fk")
    from_column: Mapped[str] = mapped_column(String, default="")
    to_column: Mapped[str] = mapped_column(String, default="")

    ontology: Mapped["Ontology"] = relationship(back_populates="links")


class OntologyFunction(Base):
    __tablename__ = "ontology_functions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ontology_id: Mapped[str] = mapped_column(String, ForeignKey("ontologies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    handler: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    input_schema: Mapped[str] = mapped_column(Text, default="{}")
    output_schema: Mapped[str] = mapped_column(Text, default="{}")
    caching_ttl: Mapped[str] = mapped_column(String, default="0")

    ontology: Mapped["Ontology"] = relationship(back_populates="functions")
