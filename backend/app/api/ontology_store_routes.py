from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.api.deps import get_current_user, get_project_for_owner
from app.schemas.ontology_store import YAMLImportRequest, YAMLImportResponse, OntologyObjectSummary
from app.services.ontology_store import OntologyStore
from app.services.ontology_importer import OntologyImporter

router = APIRouter(tags=["ontology-store"])


def _get_tenant_id(project) -> int:
    return project.tenant_id or project.owner_id


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
