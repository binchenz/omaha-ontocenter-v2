"""Domain models for ontology engine."""

from dataclasses import dataclass


@dataclass
class Column:
    """Database column metadata."""

    name: str
    type: str
    nullable: bool


@dataclass
class Table:
    """Database table schema."""

    name: str
    columns: list[Column]


@dataclass
class OntologyObject:
    """Ontology object with semantic mapping."""

    name: str
    table: Table
    properties: dict[str, str]  # property_name -> column_name
