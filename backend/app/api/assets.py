"""
Asset management endpoints for Phase 2.2.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.asset import DatasetAsset, DataLineage
from app.schemas.asset import (
    Asset as AssetSchema,
    AssetCreate,
    AssetUpdate,
    AssetWithLineage,
    Lineage as LineageSchema,
)
from app.api.deps import get_current_user

router = APIRouter()


def _get_project(project_id: int, current_user: User, db: Session) -> Project:
    """Fetch project and verify ownership, raising HTTP errors on failure."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return project


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
    _get_project(project_id, current_user, db)

    # Create asset
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
    db.flush()  # Get asset ID before creating lineage

    # Create lineage records
    lineage_records = []

    # Base table lineage
    lineage_records.append(
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
    )

    # Join lineage
    if asset_in.joins:
        for join in asset_in.joins:
            lineage_records.append(
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
            )

    # Add all lineage records
    for lineage in lineage_records:
        db.add(lineage)

    db.commit()
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
    _get_project(project_id, current_user, db)

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
    _get_project(project_id, current_user, db)
    return _get_asset(asset_id, project_id, db)


@router.delete("/{project_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    project_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an asset."""
    _get_project(project_id, current_user, db)
    asset = _get_asset(asset_id, project_id, db)
    db.delete(asset)
    db.commit()
    return None


@router.get("/{project_id}/assets/{asset_id}/lineage", response_model=List[LineageSchema])
def get_asset_lineage(
    project_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get lineage information for an asset."""
    _get_project(project_id, current_user, db)
    _get_asset(asset_id, project_id, db)

    return (
        db.query(DataLineage)
        .filter(DataLineage.asset_id == asset_id)
        .order_by(DataLineage.created_at.asc())
        .all()
    )
