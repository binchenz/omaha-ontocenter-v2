from pydantic import BaseModel
from typing import Optional


class AgentChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ToolCallRecord(BaseModel):
    tool_name: str
    params: dict
    result_summary: str


class AgentChatResponse(BaseModel):
    response: str
    tool_calls: list[ToolCallRecord] = []
    sources: list[str] = []
