"""
Chat API endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.chat_session import ChatSession, ChatMessage
from app.models.project import Project
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    SendMessageRequest,
    SendMessageResponse
)
from app.services.chat import ChatService


router = APIRouter()


@router.post("/chat/{project_id}/sessions", response_model=ChatSessionResponse)
def create_chat_session(
    project_id: int,
    session_data: ChatSessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new chat session."""
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create session
    chat_session = ChatSession(
        project_id=project_id,
        user_id=session_data.user_id,
        title=session_data.title
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    return chat_session


@router.get("/chat/{project_id}/sessions", response_model=List[ChatSessionResponse])
def list_chat_sessions(
    project_id: int,
    db: Session = Depends(get_db)
):
    """List all chat sessions for a project."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.project_id == project_id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return sessions


@router.post("/chat/{project_id}/sessions/{session_id}/message", response_model=SendMessageResponse)
def send_message(
    project_id: int,
    session_id: int,
    request: SendMessageRequest,
    db: Session = Depends(get_db)
):
    """Send a message and get response."""
    # Verify session exists
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get project config
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Call chat service
    chat_service = ChatService(project_id=project_id, db=db)
    result = chat_service.send_message(
        session_id=session_id,
        user_message=request.message,
        config_yaml=project.omaha_config,
        llm_provider="deepseek"  # TODO: Make configurable
    )

    return SendMessageResponse(**result)


@router.delete("/chat/{project_id}/sessions/{session_id}")
def delete_chat_session(
    project_id: int,
    session_id: int,
    db: Session = Depends(get_db)
):
    """Delete a chat session."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()

    return {"message": "Session deleted"}
