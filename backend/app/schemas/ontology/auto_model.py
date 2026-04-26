from pydantic import BaseModel, Field
from typing import Literal


SEMANTIC_TYPES = [
    "text", "number", "integer", "float", "boolean",
    "date", "datetime", "timestamp",
    "currency_cny", "currency_usd",
    "percentage", "ratio",
    "phone", "email", "address", "province", "city",
    "order_status", "approval_status",
    "quantity", "weight_kg", "weight_g", "volume_l",
    "stock_code", "url", "id",
]


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool = True

class TableSummaryResponse(BaseModel):
    name: str
    row_count: int
    columns: list[ColumnInfo]
    sample_values: dict[str, list[str]]

class ScanRequest(BaseModel):
    datasource_id: str

class ScanResponse(BaseModel):
    tables: list[TableSummaryResponse]

class InferRequest(BaseModel):
    datasource_id: str
    tables: list[str]

class TableClassification(BaseModel):
    name: str
    category: Literal["business", "system", "temporary", "unknown"] = "unknown"
    confidence: float = 0.5
    description: str = ""

class InferredProperty(BaseModel):
    name: str
    data_type: str
    semantic_type: str | None = None
    description: str = ""
    is_computed: bool = False
    expression: str | None = None

class InferredObject(BaseModel):
    name: str
    source_entity: str
    description: str = ""
    business_context: str = ""
    domain: str = ""
    datasource_id: str = ""
    datasource_type: str = "sql"
    properties: list[InferredProperty] = []
    suggested_health_rules: list[dict] = []
    suggested_computed_properties: list[dict] = []

class InferredRelationship(BaseModel):
    name: str
    from_object: str
    to_object: str
    relationship_type: str = "many_to_one"
    from_field: str
    to_field: str = "id"

class InferResponse(BaseModel):
    objects: list[InferredObject]
    relationships: list[InferredRelationship] = []
    warnings: list[str] = []

class ConfirmRequest(BaseModel):
    objects: list[InferredObject]
    relationships: list[InferredRelationship] = []

class ConfirmResponse(BaseModel):
    objects_created: int = 0
    objects_updated: int = 0
    relationships_created: int = 0
