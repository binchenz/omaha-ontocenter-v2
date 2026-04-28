"""SessionManager: load and save chat history from the database."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.chat.chat_session import ChatMessage

class SessionManager:
    @staticmethod
    def load_history(db: Session, session_id: int, limit: int = 20) -> list[dict]:
        """Load recent ChatMessage records, return as [{role, content}]."""
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return [{"role": m.role, "content": m.content} for m in reversed(messages)]

    @staticmethod
    def save_messages(
        db: Session,
        session_id: int,
        user_message: str,
        assistant_message: str,
        chart_config: dict[str, Any] | None = None,
    ) -> None:
        """Save user + assistant messages to ChatMessage table."""
        db.add(ChatMessage(session_id=session_id, role="user", content=user_message))
        db.add(
            ChatMessage(
                session_id=session_id,
                role="assistant",
                content=assistant_message,
                chart_config=json.dumps(chart_config) if chart_config else None,
            )
        )
        db.commit()
