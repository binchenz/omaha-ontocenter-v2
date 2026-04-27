from typing import Optional, List
from pydantic import BaseModel


class PropertyConfig(BaseModel):
    name: str
    column: Optional[str] = None
    type: str = "string"
    semantic_type: Optional[str] = None
    description: Optional[str] = None


class RelationshipConfig(BaseModel):
    name: str
    to_object: str
    type: str = "one_to_many"
    join_condition: dict = {}


class ObjectConfig(BaseModel):
    name: str
    datasource: str
    table: Optional[str] = None
    api_name: Optional[str] = None
    primary_key: Optional[str] = None
    description: Optional[str] = None
    properties: List[PropertyConfig] = []
    relationships: List[RelationshipConfig] = []


class DatasourceConfig(BaseModel):
    id: str
    name: Optional[str] = None
    type: str
    connection: dict = {}


class OntologyModel(BaseModel):
    datasources: List[DatasourceConfig] = []
    objects: List[ObjectConfig] = []


class GenerateYamlRequest(BaseModel):
    model: OntologyModel


class GenerateYamlResponse(BaseModel):
    yaml: str
    valid: bool = True
