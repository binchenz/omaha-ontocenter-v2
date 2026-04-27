"""
Chat API endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth.user import User
from app.models.chat.chat_session import ChatSession
from app.schemas.chat.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    SendMessageRequest,
    SendMessageResponse
)
from app.services.agent.chat_service import ChatServiceV2
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
async def send_message(
    project_id: int,
    session_id: int,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a message and get response (uses new ChatServiceV2 layered agent)."""
    project = get_project_for_owner(project_id, current_user, db)

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.project_id == project_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    chat_service = ChatServiceV2(project=project, db=db)
    result = await chat_service.send_message(
        session_id=session_id,
        user_message=request.message,
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


@router.post("/chat/{project_id}/sessions/{session_id}/upload")
async def upload_file_in_chat(
    project_id: int,
    session_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a file within a chat session, persist it, and return a quality report."""
    import pandas as pd
    from app.services.data.cleaner import DataCleaner
    from app.services.data.uploaded_table_store import UploadedTableStore

    get_project_for_owner(project_id, current_user, db)

    safe_name = Path(file.filename or "upload.bin").name
    upload_dir = (Path("data/uploads") / str(project_id)).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_name
    content = await file.read()
    file_path.write_bytes(content)

    table_name = Path(safe_name).stem
    try:
        if safe_name.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
    except Exception as e:
        return {
            "success": False,
            "error": f"无法解析文件: {e}",
            "file_path": str(file_path),
            "filename": safe_name,
        }

    UploadedTableStore.save(project_id, session_id, table_name, df)

    tables = UploadedTableStore.load_all(project_id, session_id)
    quality_report = DataCleaner.assess(tables).to_dict()

    return {
        "success": True,
        "file_path": str(file_path),
        "filename": safe_name,
        "table_name": table_name,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": [{"name": c, "type": str(df[c].dtype)} for c in df.columns],
        "quality_report": quality_report,
    }
