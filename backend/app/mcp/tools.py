"""MCP Server tools — thin wrappers delegating to omaha_service and DB models."""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.asset import DatasetAsset, DataLineage
from app.services.omaha import omaha_service
from app.services.semantic import semantic_service


def list_objects(config_yaml: str) -> Dict[str, Any]:
    """Return all ontology object types defined in the config."""
    result = omaha_service.build_ontology(config_yaml)
    if not result.get("valid"):
        return {"success": False, "error": result.get("error", "Invalid configuration")}
    objects = result["ontology"].get("objects", [])
    return {
        "success": True,
        "objects": [
            {
                "name": obj.get("name"),
                "description": obj.get("description", ""),
                "table": obj.get("table"),
            }
            for obj in objects
        ],
    }


def get_schema(config_yaml: str, object_type: str) -> Dict[str, Any]:
    """Return column schema enriched with semantic metadata for a given object type."""
    result = semantic_service.get_schema_with_semantics(config_yaml, object_type)
    if result.get("success"):
        return result
    # Fallback to basic schema
    return omaha_service.get_object_schema(config_yaml, object_type)


def get_relationships(config_yaml: str, object_type: str) -> Dict[str, Any]:
    """Return available relationships for a given object type."""
    rels = omaha_service.get_relationships(config_yaml, object_type)
    return {"success": True, "relationships": rels}


def query_data(
    config_yaml: str,
    object_type: str,
    selected_columns: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    joins: Optional[List[Dict[str, Any]]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Query objects from the datasource defined in the config."""
    return omaha_service.query_objects(
        config_yaml=config_yaml,
        object_type=object_type,
        selected_columns=selected_columns,
        filters=filters,
        joins=joins,
        limit=limit,
    )


def save_asset(
    db: Session,
    project_id: int,
    created_by: int,
    name: str,
    base_object: str,
    description: str = "",
    selected_columns: Optional[List[str]] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    joins: Optional[List[Dict[str, Any]]] = None,
    row_count: Optional[int] = None,
) -> Dict[str, Any]:
    """Persist a dataset asset and record its lineage."""
    asset = DatasetAsset(
        project_id=project_id,
        name=name,
        description=description,
        base_object=base_object,
        selected_columns=selected_columns or [],
        filters=filters or [],
        joins=joins or [],
        row_count=row_count,
        created_by=created_by,
    )
    db.add(asset)
    db.flush()  # get asset.id before lineage insert

    lineage = DataLineage(
        asset_id=asset.id,
        lineage_type="query",
        source_type="table",
        source_id=base_object,
        source_name=base_object,
        transformation={
            "selected_columns": selected_columns or [],
            "filters": filters or [],
            "joins": joins or [],
        },
    )
    db.add(lineage)
    db.commit()
    db.refresh(asset)

    return {
        "success": True,
        "asset_id": asset.id,
        "name": asset.name,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
    }


def list_assets(db: Session, project_id: int) -> Dict[str, Any]:
    """List all dataset assets for a project."""
    assets = (
        db.query(
            DatasetAsset.id,
            DatasetAsset.name,
            DatasetAsset.description,
            DatasetAsset.base_object,
            DatasetAsset.row_count,
            DatasetAsset.created_at,
        )
        .filter(DatasetAsset.project_id == project_id)
        .all()
    )
    return {
        "success": True,
        "assets": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "base_object": a.base_object,
                "row_count": a.row_count,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in assets
        ],
    }


def get_lineage(db: Session, asset_id: int) -> Dict[str, Any]:
    """Return lineage records for a dataset asset."""
    asset = db.query(DatasetAsset).filter(DatasetAsset.id == asset_id).first()
    if not asset:
        return {"success": False, "error": f"Asset {asset_id} not found"}

    lineage_records = (
        db.query(DataLineage).filter(DataLineage.asset_id == asset_id).all()
    )
    return {
        "success": True,
        "asset_id": asset_id,
        "asset_name": asset.name,
        "lineage": [
            {
                "id": rec.id,
                "lineage_type": rec.lineage_type,
                "source_type": rec.source_type,
                "source_id": rec.source_id,
                "source_name": rec.source_name,
                "transformation": rec.transformation,
                "created_at": rec.created_at.isoformat() if rec.created_at else None,
            }
            for rec in lineage_records
        ],
    }
