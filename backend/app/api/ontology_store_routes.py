from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user, get_project_for_owner
from app.schemas.ontology_store import YAMLImportRequest, YAMLImportResponse, OntologyObjectSummary
from app.schemas.auto_model import (
    ScanRequest, ScanResponse, TableSummaryResponse, ColumnInfo,
    InferRequest, InferResponse,
    ConfirmRequest, ConfirmResponse,
)
from app.services.ontology_store import OntologyStore
from app.services.ontology_importer import OntologyImporter
from app.services.schema_scanner import SchemaScanner
from app.services.ontology_inferrer import OntologyInferrer

router = APIRouter(tags=["ontology-store"])


def _get_tenant_id(project) -> int:
    return project.tenant_id or project.owner_id


def _get_datasource_url(project, datasource_id: str) -> str:
    """Extract connection URL from project's YAML config for a given datasource_id."""
    import yaml
    config = yaml.safe_load(project.omaha_config or "")
    if not isinstance(config, dict):
        return ""
    for ds in config.get("datasources", []):
        if ds.get("id") == datasource_id:
            conn = ds.get("connection", {})
            return conn.get("url", "")
    return ""


@router.post("/{project_id}/import", response_model=YAMLImportResponse)
def import_yaml(
    project_id: int,
    request: YAMLImportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    importer = OntologyImporter(db)
    result = importer.import_yaml(
        tenant_id=_get_tenant_id(project),
        yaml_content=request.yaml_content,
    )
    return YAMLImportResponse(**result)


@router.get("/{project_id}/objects", response_model=list[OntologyObjectSummary])
def list_objects(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    store = OntologyStore(db)
    objects = store.list_objects(tenant_id=_get_tenant_id(project))
    return [
        OntologyObjectSummary(
            id=obj.id, name=obj.name, source_entity=obj.source_entity,
            datasource_id=obj.datasource_id, datasource_type=obj.datasource_type,
            description=obj.description, domain=obj.domain,
            property_count=len(obj.properties),
        )
        for obj in objects
    ]


@router.get("/{project_id}/full")
def get_full_ontology(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    store = OntologyStore(db)
    return store.get_full_ontology(tenant_id=_get_tenant_id(project))


@router.post("/{project_id}/scan", response_model=ScanResponse)
def scan_tables(
    project_id: int,
    request: ScanRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    url = _get_datasource_url(project, request.datasource_id)
    if not url:
        raise HTTPException(status_code=400, detail=f"Datasource '{request.datasource_id}' not found or has no URL")
    scanner = SchemaScanner(url)
    try:
        summaries = scanner.scan_all()
        tables = [
            TableSummaryResponse(
                name=s.name, row_count=s.row_count,
                columns=[ColumnInfo(name=c["name"], type=c["type"], nullable=c.get("nullable", True)) for c in s.columns],
                sample_values=s.sample_values,
            )
            for s in summaries
        ]
        return ScanResponse(tables=tables)
    finally:
        scanner.close()


@router.post("/{project_id}/infer", response_model=InferResponse)
def infer_ontology(
    project_id: int,
    request: InferRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    url = _get_datasource_url(project, request.datasource_id)
    if not url:
        raise HTTPException(status_code=400, detail=f"Datasource '{request.datasource_id}' not found or has no URL")

    scanner = SchemaScanner(url)
    inferrer = OntologyInferrer()
    try:
        objects = []
        warnings = []
        for table_name in request.tables:
            summary = scanner.scan_table(table_name)
            result = inferrer.infer_table(summary, datasource_id=request.datasource_id)
            if result:
                objects.append(result)
            else:
                warnings.append(f"表 {table_name} 推断失败，需手动配置")
        relationships = inferrer.infer_relationships_by_naming(objects)
        return InferResponse(objects=objects, relationships=relationships, warnings=warnings)
    finally:
        scanner.close()


@router.post("/{project_id}/confirm", response_model=ConfirmResponse)
def confirm_ontology(
    project_id: int,
    request: ConfirmRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    tenant_id = _get_tenant_id(project)
    importer = OntologyImporter(db)
    config = {
        "datasources": [
            {"id": obj.datasource_id, "type": obj.datasource_type}
            for obj in request.objects
        ],
        "ontology": {
            "objects": [
                {
                    "name": obj.name,
                    "datasource": obj.datasource_id,
                    "source_entity": obj.source_entity,
                    "description": obj.description,
                    "business_context": obj.business_context,
                    "domain": obj.domain,
                    "properties": [
                        {"name": p.name, "type": p.data_type, "semantic_type": p.semantic_type, "description": p.description}
                        for p in obj.properties
                    ],
                }
                for obj in request.objects
            ],
            "relationships": [
                {
                    "name": r.name,
                    "from_object": r.from_object,
                    "to_object": r.to_object,
                    "type": r.relationship_type,
                    "from_field": r.from_field,
                    "to_field": r.to_field,
                }
                for r in request.relationships
            ],
        },
    }
    result = importer.import_dict(tenant_id=tenant_id, config=config)
    return ConfirmResponse(**result)
