from pydantic import BaseModel
from typing import Optional, List

class AgentChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ToolCallRecord(BaseModel):
    tool_name: str
    params: dict
    result_summary: str

class AgentChatResponse(BaseModel):
    response: str
    tool_calls: List[ToolCallRecord] = []
    sources: List[str] = []
    data_table: Optional[List[dict]] = None
    chart_config: Optional[dict] = None
    sql: Optional[str] = None
