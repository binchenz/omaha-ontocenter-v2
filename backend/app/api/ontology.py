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


from app.schemas.ontology import GenerateYamlRequest, GenerateYamlResponse


@router.post("/generate", response_model=GenerateYamlResponse)
def generate_yaml(
    req: GenerateYamlRequest,
    user: User = Depends(get_current_user),
):
    """Convert OntologyModel JSON to YAML string."""
    import yaml as pyyaml

    model = req.model
    config = {}

    if model.datasources:
        config["datasources"] = []
        for ds in model.datasources:
            ds_dict = {"id": ds.id, "type": ds.type}
            if ds.name:
                ds_dict["name"] = ds.name
            if ds.connection:
                ds_dict["connection"] = dict(ds.connection)
            config["datasources"].append(ds_dict)

    if model.objects:
        config["ontology"] = {"objects": []}
        for obj in model.objects:
            obj_dict = {"name": obj.name, "datasource": obj.datasource}
            if obj.table:
                obj_dict["table"] = obj.table
            if obj.api_name:
                obj_dict["api_name"] = obj.api_name
            if obj.primary_key:
                obj_dict["primary_key"] = obj.primary_key
            if obj.description:
                obj_dict["description"] = obj.description
            if obj.properties:
                obj_dict["properties"] = []
                for prop in obj.properties:
                    p = {"name": prop.name, "type": prop.type}
                    if prop.column:
                        p["column"] = prop.column
                    if prop.semantic_type:
                        p["semantic_type"] = prop.semantic_type
                    if prop.description:
                        p["description"] = prop.description
                    obj_dict["properties"].append(p)
            if obj.relationships:
                obj_dict["relationships"] = []
                for rel in obj.relationships:
                    r = {
                        "name": rel.name,
                        "to_object": rel.to_object,
                        "type": rel.type,
                    }
                    if rel.join_condition:
                        r["join_condition"] = dict(rel.join_condition)
                    obj_dict["relationships"].append(r)
            config["ontology"]["objects"].append(obj_dict)

    yaml_str = pyyaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return GenerateYamlResponse(yaml=yaml_str, valid=True)
