"""
Chat API endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.chat_session import ChatSession
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    SendMessageRequest,
    SendMessageResponse
)
from app.services.chat import ChatService
from app.api.deps import get_current_user, get_project_for_owner


router = APIRouter()


@router.post("/chat/{project_id}/sessions", response_model=ChatSessionResponse)
def create_chat_session(
    project_id: int,
    session_data: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chat session."""
    get_project_for_owner(project_id, current_user, db)

    chat_session = ChatSession(
        project_id=project_id,
        user_id=current_user.id,
        title=session_data.title
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)

    return chat_session


@router.get("/chat/{project_id}/sessions", response_model=List[ChatSessionResponse])
def list_chat_sessions(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chat sessions for a project."""
    get_project_for_owner(project_id, current_user, db)

    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.project_id == project_id, ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return sessions


@router.post("/chat/{project_id}/sessions/{session_id}/message", response_model=SendMessageResponse)
def send_message(
    project_id: int,
    session_id: int,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message and get response."""
    project = get_project_for_owner(project_id, current_user, db)

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.project_id == project_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    chat_service = ChatService(project_id=project_id, db=db)
    result = chat_service.send_message(
        session_id=session_id,
        user_message=request.message,
        config_yaml=project.omaha_config,
        llm_provider="deepseek"
    )

    return SendMessageResponse(**result)


@router.delete("/chat/{project_id}/sessions/{session_id}")
def delete_chat_session(
    project_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session."""
    get_project_for_owner(project_id, current_user, db)

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.project_id == project_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()

    return {"message": "Session deleted"}
