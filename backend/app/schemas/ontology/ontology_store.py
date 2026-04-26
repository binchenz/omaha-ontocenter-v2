from pydantic import BaseModel
from typing import Optional


class YAMLImportRequest(BaseModel):
    yaml_content: str


class YAMLImportResponse(BaseModel):
    objects_created: int
    relationships_created: int


class OntologyObjectSummary(BaseModel):
    id: int
    name: str
    source_entity: str
    datasource_id: str
    datasource_type: str
    description: Optional[str] = None
    domain: Optional[str] = None
    property_count: int = 0

    class Config:
        from_attributes = True
