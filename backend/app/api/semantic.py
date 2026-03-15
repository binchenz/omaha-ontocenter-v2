"""
Semantic layer API endpoints.
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user, get_project_for_owner
from app.services.semantic import semantic_service

router = APIRouter()


class SemanticConfigUpdate(BaseModel):
    config: str


class FormulaTestRequest(BaseModel):
    object_type: str
    formula: str
    return_type: str = "string"


@router.get("/projects/{project_id}/semantic")
def get_semantic_config(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get current semantic config with parsed metadata."""
    project = get_project_for_owner(project_id, current_user, db)
    config_yaml = project.omaha_config or ""
    parsed = semantic_service.parse_config(config_yaml)
    return {"config": config_yaml, "parsed": parsed}


@router.put("/projects/{project_id}/semantic")
def update_semantic_config(
    project_id: int,
    body: SemanticConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Save updated semantic config (validates YAML before saving)."""
    project = get_project_for_owner(project_id, current_user, db)
    result = semantic_service.parse_config(body.config)
    if not result["valid"]:
        raise HTTPException(status_code=400, detail=result["error"])
    project.omaha_config = body.config
    db.commit()
    return {"success": True}


@router.post("/projects/{project_id}/semantic/test-formula")
def test_formula(
    project_id: int,
    body: FormulaTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Test a formula by expanding it to SQL."""
    project = get_project_for_owner(project_id, current_user, db)
    parsed = semantic_service.parse_config(project.omaha_config or "")
    if not parsed["valid"]:
        raise HTTPException(status_code=400, detail="Invalid project config")
    obj = parsed["objects"].get(body.object_type)
    if not obj:
        raise HTTPException(status_code=404, detail=f"Object '{body.object_type}' not found")
    try:
        sql_expr = semantic_service.expand_formula(body.formula, obj["property_map"])
    except ValueError as e:
        return {"sql": None, "sample": [], "error": str(e)}
    return {"sql": f"SELECT {sql_expr} AS result FROM <table> LIMIT 100",
            "sample": [], "error": None}


# ─── Utility endpoints (no project context needed) ────────────────────────────

class ParseConfigRequest(BaseModel):
    config_yaml: str


class ExpandFormulaRequest(BaseModel):
    formula: str
    property_map: Dict[str, str]


class GetSchemaRequest(BaseModel):
    config_yaml: str
    object_type: str


@router.post("/semantic/parse")
async def parse_semantic_config(
    request: ParseConfigRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Parse YAML config and extract semantic metadata."""
    return semantic_service.parse_config(request.config_yaml)


@router.post("/semantic/test-formula")
async def test_formula_util(
    request: ExpandFormulaRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Expand a formula using the given property map."""
    try:
        sql = semantic_service.expand_formula(request.formula, request.property_map)
        return {"success": True, "sql": sql}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/semantic/schema")
async def get_schema_util(
    request: GetSchemaRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get schema enriched with semantic metadata."""
    result = semantic_service.get_schema_with_semantics(request.config_yaml, request.object_type)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
