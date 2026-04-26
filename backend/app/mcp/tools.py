"""MCP Server tools — thin wrappers delegating to omaha_service and DB models."""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.asset import DatasetAsset, DataLineage
from app.services.legacy.financial.omaha import omaha_service
from app.services.semantic.service import semantic_service


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


def screen_stocks(
    config_yaml: str,
    metric_objects: List[Dict[str, Any]],
    stock_filters: Optional[List[Dict[str, Any]]] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "desc",
    limit: int = 10,
) -> Dict[str, Any]:
    """Screen A-share stocks across multiple ontology objects (financial + valuation + technical)."""
    try:
        limit = min(limit, 20)
        stock_filters = stock_filters or []

        # Step 1: Get candidate stock list (max 200)
        stock_result = omaha_service.query_objects(
            config_yaml, "Stock",
            selected_columns=["Stock.ts_code", "Stock.name", "Stock.industry"],
            filters=stock_filters,
            limit=200,
        )
        if not stock_result.get("success"):
            return {"error": f"获取股票列表失败: {stock_result.get('error')}"}

        stocks = stock_result.get("data", [])
        if not stocks:
            return {"data": [], "count": 0, "message": "没有找到符合条件的股票"}

        # Step 2: Fetch metric data for each stock and merge
        results = []
        for stock in stocks:
            ts_code = stock.get("ts_code")
            row = {"ts_code": ts_code, "name": stock.get("name"), "industry": stock.get("industry")}

            for metric_obj in metric_objects:
                obj_name = metric_obj.get("object")
                columns = metric_obj.get("columns", [])
                cols = [f"{obj_name}.{c}" for c in columns] if columns else None
                r = omaha_service.query_objects(
                    config_yaml, obj_name,
                    selected_columns=cols,
                    filters=[{"field": "ts_code", "operator": "=", "value": ts_code}],
                    limit=1,
                )
                if r.get("success") and r.get("data"):
                    row.update(r["data"][0])

            if len(row) > 3:
                results.append(row)

        # Step 3: Apply metric filters client-side
        for metric_obj in metric_objects:
            for f in metric_obj.get("filters", []):
                field, op, val = f.get("field"), f.get("operator", ">="), f.get("value")
                filtered = []
                for row in results:
                    v = row.get(field)
                    if v is None:
                        continue
                    try:
                        v, val_f = float(v), float(val)
                        if op in (">=", "=>") and v >= val_f:
                            filtered.append(row)
                        elif op == ">" and v > val_f:
                            filtered.append(row)
                        elif op in ("<=", "=<") and v <= val_f:
                            filtered.append(row)
                        elif op == "<" and v < val_f:
                            filtered.append(row)
                        elif op == "=" and v == val_f:
                            filtered.append(row)
                    except (TypeError, ValueError):
                        pass
                results = filtered

        # Step 4: Sort and limit
        if sort_by and results:
            results.sort(key=lambda x: float(x.get(sort_by, 0) or 0), reverse=(sort_order == "desc"))
        results = results[:limit]

        return {"success": True, "data": results, "count": len(results), "total_screened": len(stocks)}

    except Exception as e:
        return {"error": str(e)}


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
