"""
Semantic layer API endpoints.
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.user import User
from app.api.deps import get_current_user
from app.services.semantic import semantic_service

router = APIRouter()


class ParseConfigRequest(BaseModel):
    """Request schema for parsing semantic config."""
    config_yaml: str


class ExpandFormulaRequest(BaseModel):
    """Request schema for testing formula expansion."""
    formula: str
    property_map: Dict[str, str]


class GetSchemaRequest(BaseModel):
    """Request schema for getting schema with semantics."""
    config_yaml: str
    object_type: str


@router.post("/parse")
async def parse_semantic_config(
    request: ParseConfigRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Parse YAML config and extract semantic metadata."""
    return semantic_service.parse_config(request.config_yaml)


@router.post("/test-formula")
async def test_formula(
    request: ExpandFormulaRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Expand a formula using the given property map and return the SQL."""
    try:
        sql = semantic_service.expand_formula(request.formula, request.property_map)
        return {"success": True, "sql": sql}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/schema")
async def get_schema_with_semantics(
    request: GetSchemaRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get schema enriched with semantic metadata for a given object type."""
    result = semantic_service.get_schema_with_semantics(request.config_yaml, request.object_type)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
