"""
Asset Pydantic schemas.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


class AssetBase(BaseModel):
    """Base asset schema."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    base_object: str = Field(..., min_length=1)


class AssetCreate(AssetBase):
    """Asset creation schema."""

    selected_columns: Optional[List[str]] = None
    filters: Optional[List[Dict[str, Any]]] = None
    joins: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None


class AssetUpdate(BaseModel):
    """Asset update schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None


class LineageBase(BaseModel):
    """Base lineage schema."""

    lineage_type: str
    source_type: str
    source_id: Optional[str] = None
    source_name: Optional[str] = None
    transformation: Optional[Dict[str, Any]] = None


class Lineage(LineageBase):
    """Lineage response schema."""

    id: int
    asset_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AssetInDB(AssetBase):
    """Asset in database schema."""

    id: int
    project_id: int
    selected_columns: Optional[List[str]] = None
    filters: Optional[List[Dict[str, Any]]] = None
    joins: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class Asset(AssetInDB):
    """Asset response schema."""

    pass


class AssetWithLineage(Asset):
    """Asset with lineage information."""

    lineage: List[Lineage] = []
