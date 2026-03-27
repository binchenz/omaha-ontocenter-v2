"""Schemas for public query API."""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    object_type: str = Field(..., description="Object type to query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Query filters")
    limit: int = Field(100, ge=1, le=1000, description="Result limit")
    offset: int = Field(0, ge=0, description="Result offset")
    format: bool = Field(False, description="Apply semantic formatting (percentage, currency)")
    order_by: Optional[str] = Field(None, description="Field to sort by")
    order: Optional[str] = Field("desc", description="Sort order: asc or desc")


class QueryResponse(BaseModel):
    data: List[Dict[str, Any]]
    count: int
    limit: int
    offset: int


class ObjectInfo(BaseModel):
    object_type: str
    description: str


class ObjectListResponse(BaseModel):
    objects: List[ObjectInfo]


class FieldInfo(BaseModel):
    name: str
    type: str
    semantic_type: Optional[str] = None
    description: str


class ComputedPropertyInfo(BaseModel):
    name: str
    expression: str
    semantic_type: Optional[str] = None
    description: str


class SchemaResponse(BaseModel):
    object_type: str
    description: Optional[str] = None
    business_context: Optional[str] = None
    fields: List[FieldInfo]
    computed_properties: Optional[List[ComputedPropertyInfo]] = None
