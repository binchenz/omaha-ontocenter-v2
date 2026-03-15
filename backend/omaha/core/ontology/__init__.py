"""Ontology engine for schema discovery and semantic mapping."""

from omaha.core.ontology.models import Column, Table, OntologyObject
from omaha.core.ontology.discovery import discover_schema, discover_table
from omaha.core.ontology.mapper import map_ontology_object, validate_mapping
from omaha.core.ontology.engine import OntologyEngine

__all__ = [
    "Column",
    "Table",
    "OntologyObject",
    "discover_schema",
    "discover_table",
    "map_ontology_object",
    "validate_mapping",
    "OntologyEngine",
]
