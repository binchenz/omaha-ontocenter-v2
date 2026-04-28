"""
Asset management endpoints for Phase 2.2.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth.user import User
from app.models.ontology.asset import DatasetAsset, DataLineage
from app.schemas.project.asset import (
    Asset as AssetSchema,
    AssetCreate,
    Lineage as LineageSchema,
)
from app.api.deps import get_current_user, get_project_for_owner

router = APIRouter()


def _get_asset(asset_id: int, project_id: int, db: Session) -> DatasetAsset:
    """Fetch asset by id and project, raising HTTP 404 if not found."""
    asset = (
        db.query(DatasetAsset)
        .filter(DatasetAsset.id == asset_id, DatasetAsset.project_id == project_id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


@router.post("/{project_id}/assets", response_model=AssetSchema, status_code=status.HTTP_201_CREATED)
def save_asset(
    project_id: int,
    asset_in: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save query as asset."""
    get_project_for_owner(project_id, current_user, db)

    asset = DatasetAsset(
        project_id=project_id,
        name=asset_in.name,
        description=asset_in.description,
        base_object=asset_in.base_object,
        selected_columns=asset_in.selected_columns or [],
        filters=asset_in.filters or [],
        joins=asset_in.joins or [],
        row_count=asset_in.row_count,
        created_by=current_user.id,
    )
    db.add(asset)
    db.flush()

    lineage_records = [
        DataLineage(
            asset_id=asset.id,
            lineage_type="query",
            source_type="table",
            source_id=asset_in.base_object,
            source_name=asset_in.base_object,
            transformation={
                "selected_columns": asset_in.selected_columns or [],
                "filters": asset_in.filters or [],
            },
        )
    ] + [
        DataLineage(
            asset_id=asset.id,
            lineage_type="join",
            source_type="table",
            source_id=join.get("target_object"),
            source_name=join.get("target_object"),
            transformation={
                "relationship": join.get("relationship"),
                "join_type": join.get("join_type"),
            },
        )
        for join in (asset_in.joins or [])
    ]

    db.add_all(lineage_records)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save asset")
    db.refresh(asset)

    return asset


@router.get("/{project_id}/assets", response_model=List[AssetSchema])
def list_assets(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all assets for a project."""
    get_project_for_owner(project_id, current_user, db)

    assets = (
        db.query(DatasetAsset)
        .filter(DatasetAsset.project_id == project_id)
        .order_by(DatasetAsset.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return assets


@router.get("/{project_id}/assets/{asset_id}", response_model=AssetSchema)
def get_asset(
    project_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get asset details."""
    get_project_for_owner(project_id, current_user, db)
    return _get_asset(asset_id, project_id, db)


@router.delete("/{project_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    project_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an asset."""
    get_project_for_owner(project_id, current_user, db)
    asset = _get_asset(asset_id, project_id, db)
    db.delete(asset)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete asset")
    return None


@router.get("/{project_id}/assets/{asset_id}/lineage", response_model=List[LineageSchema])
def get_asset_lineage(
    project_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get lineage information for an asset."""
    get_project_for_owner(project_id, current_user, db)
    _get_asset(asset_id, project_id, db)

    return (
        db.query(DataLineage)
        .filter(DataLineage.asset_id == asset_id)
        .order_by(DataLineage.created_at.asc())
        .all()
    )
