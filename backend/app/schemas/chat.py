"""
Chat API schemas.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    """Schema for creating a chat session."""
    title: Optional[str] = None


class ChatSessionResponse(BaseModel):
    """Schema for chat session response."""
    id: int
    project_id: int
    user_id: int
    title: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    """Schema for creating a chat message."""
    session_id: int
    content: str


class ChatMessageResponse(BaseModel):
    """Schema for chat message response."""
    id: int
    session_id: int
    role: str
    content: str
    tool_calls: Optional[str]
    chart_config: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    """Schema for sending a message."""
    message: str


class StructuredItem(BaseModel):
    type: str  # "text", "options", "panel", "file_upload"
    content: str
    options: Optional[List[Dict[str, str]]] = None
    panel_type: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    accept: Optional[str] = None
    multiple: Optional[bool] = None


class SendMessageResponse(BaseModel):
    """Schema for message response with optional chart."""
    message: str
    data_table: Optional[List[Dict[str, Any]]] = None
    chart_config: Optional[Dict[str, Any]] = None
    sql: Optional[str] = None
    structured: Optional[List[StructuredItem]] = None
    setup_stage: Optional[str] = None
