from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Optional


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
    columns: List[ColumnInfo]
    sample_values: Dict[str, List[str]]

class ScanRequest(BaseModel):
    datasource_id: str

class ScanResponse(BaseModel):
    tables: List[TableSummaryResponse]

class InferRequest(BaseModel):
    datasource_id: str
    tables: List[str]

class TableClassification(BaseModel):
    name: str
    category: Literal["business", "system", "temporary", "unknown"] = "unknown"
    confidence: float = 0.5
    description: str = ""

class InferredProperty(BaseModel):
    name: str
    data_type: str
    semantic_type: Optional[str] = None
    description: str = ""
    is_computed: bool = False
    expression: Optional[str] = None

class InferredObject(BaseModel):
    name: str
    source_entity: str
    description: str = ""
    business_context: str = ""
    domain: str = ""
    datasource_id: str = ""
    datasource_type: str = "sql"
    properties: List[InferredProperty] = []
    suggested_health_rules: List[dict] = []
    suggested_computed_properties: List[dict] = []

class InferredRelationship(BaseModel):
    name: str
    from_object: str
    to_object: str
    relationship_type: str = "many_to_one"
    from_field: str
    to_field: str = "id"

class InferResponse(BaseModel):
    objects: List[InferredObject]
    relationships: List[InferredRelationship] = []
    warnings: List[str] = []

class ConfirmRequest(BaseModel):
    objects: List[InferredObject]
    relationships: List[InferredRelationship] = []

class ConfirmResponse(BaseModel):
    objects_created: int = 0
    objects_updated: int = 0
    relationships_created: int = 0
