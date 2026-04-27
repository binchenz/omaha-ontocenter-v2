from pydantic import BaseModel
from typing import Optional, Union


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
    data_table: Optional[list[dict]] = None
    chart_config: Optional[dict] = None
    sql: Optional[str] = None
