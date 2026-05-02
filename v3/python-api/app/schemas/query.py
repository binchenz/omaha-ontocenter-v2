from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime


class OAGProperty(BaseModel):
    value: Any
    semantic_type: str = "text"
    unit: str | None = None
    format: str | None = None
    source: str | None = None
    last_updated: str | None = None


class OAGLink(BaseModel):
    object_type: str
    id: str
    label: str


class OAGMatch(BaseModel):
    id: str
    label: str | None = None
    properties: dict[str, OAGProperty] = Field(default_factory=dict)
    links: dict[str, OAGLink] = Field(default_factory=dict)
    available_functions: list[str] = Field(default_factory=list)


class OAGContext(BaseModel):
    total: int
    related_objects: list[str] = Field(default_factory=list)
    suggested_queries: list[str] = Field(default_factory=list)


class OAGQueryRequest(BaseModel):
    operation: str = "search"
    object: str
    filters: dict[str, Any] | None = None
    measures: list[str] | None = None
    group_by: list[str] | None = None
    path: list[str] | None = None
    limit: int = 50
    include_links: list[str] | None = None
    include_functions: list[str] | None = None


class OAGQueryResponse(BaseModel):
    object_type: str
    matched: list[OAGMatch] = Field(default_factory=list)
    context: OAGContext
