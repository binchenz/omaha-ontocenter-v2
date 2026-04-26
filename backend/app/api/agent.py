from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.user import User
from app.api.deps import get_current_user, get_db, get_project_for_owner
from app.services.agent.legacy_agent_service import AgentService as LegacyAgentService
from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.services.ontology_store import OntologyStore
from app.services.agent_tools import AgentToolkit
from app.services.agent import AgentService
from app.services.omaha import OmahaService

router = APIRouter()


class AgentQueryRequest(BaseModel):
    """Request schema for agent query."""
    message: str
    config_yaml: str | None = None


class AgentQueryResponse(BaseModel):
    """Response schema for agent query."""
    response: str
    tool_calls: list[dict] = []


@router.post("/query", response_model=AgentQueryResponse)
async def agent_query(
    request: AgentQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Send a natural language query to the Agent."""
    tenant_id = current_user.tenant_id or current_user.id
    agent = LegacyAgentService(db, tenant_id=tenant_id, config_yaml=request.config_yaml)
    result = agent.run(request.message)
    return result


@router.get("/context")
async def agent_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get the full agent context prompt for debugging."""
    tenant_id = current_user.tenant_id or current_user.id
    agent = LegacyAgentService(db, tenant_id=tenant_id)
    return {"context": agent.get_agent_context()}


@router.post("/{project_id}/chat", response_model=AgentChatResponse)
def agent_chat(
    project_id: int,
    request: AgentChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    store = OntologyStore(db)
    tenant_id = project.tenant_id or project.owner_id
    ontology_context = store.get_full_ontology(tenant_id)

    omaha_service = OmahaService(project.omaha_config or "")
    toolkit = AgentToolkit(omaha_service=omaha_service, ontology_context=ontology_context)

    agent = AgentService(
        ontology_context=ontology_context,
        toolkit=toolkit,
    )

    result = agent.chat(request.message)
    return result
