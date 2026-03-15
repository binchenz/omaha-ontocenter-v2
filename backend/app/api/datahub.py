"""
DataHub endpoints.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import User
from app.api.deps import get_current_user
from app.services.datahub import datahub_service

router = APIRouter()


@router.get("/search")
async def search_datasets(
    query: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Search for datasets in DataHub."""
    try:
        results = await datahub_service.search_datasets(query, limit)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search datasets: {str(e)}",
        )


@router.get("/datasets/{dataset_urn:path}/schema")
async def get_dataset_schema(
    dataset_urn: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get schema for a dataset."""
    try:
        schema = await datahub_service.get_dataset_schema(dataset_urn)
        if schema is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )
        return schema
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dataset schema: {str(e)}",
        )


@router.get("/datasets/{dataset_urn:path}/properties")
async def get_dataset_properties(
    dataset_urn: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get properties for a dataset."""
    try:
        properties = await datahub_service.get_dataset_properties(dataset_urn)
        if properties is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )
        return properties
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dataset properties: {str(e)}",
        )
