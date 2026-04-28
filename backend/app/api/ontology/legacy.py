"""
Ontology endpoints.
"""
from typing import Dict, Any, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.auth.user import User
from app.api.deps import get_current_user, get_db
from app.schemas.ontology.ontology import GenerateYamlRequest, GenerateYamlResponse
from app.services.legacy.financial.omaha import omaha_service
from app.services.ontology.store import OntologyStore
from app.services.ontology.importer import OntologyImporter

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

# ── CRUD endpoints for DB-backed ontology ──────────────────────────

class OntologyObjectCreate(BaseModel):
    name: str
    source_entity: str
    datasource_id: str
    datasource_type: str = "sql"
    description: Optional[str] = None
    business_context: Optional[str] = None
    domain: Optional[str] = None

class PropertyCreate(BaseModel):
    name: str
    data_type: str
    semantic_type: Optional[str] = None
    description: Optional[str] = None

@router.get("/objects")
async def list_ontology_objects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id or current_user.id
    store = OntologyStore(db)
    objects = store.list_objects(tenant_id)
    return [{"id": o.id, "name": o.name, "source_entity": o.source_entity,
             "datasource_id": o.datasource_id, "domain": o.domain} for o in objects]

@router.get("/objects/{name}")
async def get_ontology_object(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id or current_user.id
    store = OntologyStore(db)
    obj = store.get_object(tenant_id, name)
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    return {
        "id": obj.id,
        "name": obj.name,
        "source_entity": obj.source_entity,
        "datasource_id": obj.datasource_id,
        "datasource_type": obj.datasource_type,
        "description": obj.description,
        "business_context": obj.business_context,
        "domain": obj.domain,
        "properties": [{"id": p.id, "name": p.name, "type": p.data_type,
                         "semantic_type": p.semantic_type} for p in obj.properties],
        "health_rules": [{"id": r.id, "metric": r.metric, "expression": r.expression}
                         for r in obj.health_rules],
    }

@router.post("/objects")
async def create_ontology_object(
    obj_in: OntologyObjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id or current_user.id
    store = OntologyStore(db)
    existing = store.get_object(tenant_id, obj_in.name)
    if existing:
        raise HTTPException(status_code=409, detail="Object already exists")
    obj = store.create_object(
        tenant_id=tenant_id,
        name=obj_in.name,
        source_entity=obj_in.source_entity,
        datasource_id=obj_in.datasource_id,
        datasource_type=obj_in.datasource_type,
        description=obj_in.description,
        business_context=obj_in.business_context,
        domain=obj_in.domain,
    )
    return {"id": obj.id, "name": obj.name}

@router.delete("/objects/{name}")
async def delete_ontology_object(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id or current_user.id
    store = OntologyStore(db)
    deleted = store.delete_object(tenant_id, name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Object not found")
    return {"deleted": True}

@router.post("/objects/{name}/properties")
async def add_object_property(
    name: str,
    prop_in: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id or current_user.id
    store = OntologyStore(db)
    obj = store.get_object(tenant_id, name)
    if not obj:
        raise HTTPException(status_code=404, detail="Object not found")
    prop = store.add_property(
        object_id=obj.id,
        name=prop_in.name,
        data_type=prop_in.data_type,
        semantic_type=prop_in.semantic_type,
        description=prop_in.description,
    )
    return {"id": prop.id, "name": prop.name}

@router.post("/import")
async def import_ontology_yaml(
    request: BuildOntologyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id or current_user.id
    importer = OntologyImporter(db)
    result = importer.import_yaml(tenant_id=tenant_id, yaml_content=request.config_yaml)
    return result
