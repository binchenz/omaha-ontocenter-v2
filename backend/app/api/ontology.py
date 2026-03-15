"""
Ontology endpoints.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.models.user import User
from app.api.deps import get_current_user
from app.services.omaha import omaha_service

router = APIRouter()


class ValidateConfigRequest(BaseModel):
    """Request schema for config validation."""

    config_yaml: str


class BuildOntologyRequest(BaseModel):
    """Request schema for building ontology."""

    config_yaml: str


@router.post("/validate")
async def validate_config(
    request: ValidateConfigRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Validate Omaha configuration."""
    result = omaha_service.parse_config(request.config_yaml)
    return result


@router.post("/build")
async def build_ontology(
    request: BuildOntologyRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Build ontology from configuration."""
    result = omaha_service.build_ontology(request.config_yaml)
    return result
