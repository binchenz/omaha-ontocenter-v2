from pydantic import BaseModel, Field
from typing import Any


class PropertyDef(BaseModel):
    name: str
    slug: str = ""
    description: str = ""
    semantic_type: str = "text"
    source_column: str = ""
    is_computed: bool = False
    function_ref: str | None = None
    unit: str = ""


class LinkDef(BaseModel):
    name: str
    from_object: str
    to_object: str
    type: str = "fk"
    from_column: str = ""
    to_column: str = ""


class FunctionDef(BaseModel):
    name: str
    handler: str
    description: str = ""
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    caching_ttl: str = "0"


class ObjectDef(BaseModel):
    name: str
    slug: str = ""
    description: str = ""
    table_name: str = ""
    datasource_id: str = ""
    properties: list[PropertyDef] = Field(default_factory=list)
    links: list[LinkDef] = Field(default_factory=list)
    functions: list[FunctionDef] = Field(default_factory=list)


class OntologyConfig(BaseModel):
    name: str
    slug: str = ""
    version: str = "1"
    description: str = ""
    objects: list[ObjectDef] = Field(default_factory=list)
    functions: list[FunctionDef] = Field(default_factory=list)
    links: list[LinkDef] = Field(default_factory=list)
