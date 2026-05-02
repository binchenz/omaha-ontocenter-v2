from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.ontology.store import get_ontology_objects, get_ontology_links, get_ontology_functions, get_ontology
from app.services.mcp.tool_generator import generate_tools
from app.services.mcp.skill_packager import generate_skill, generate_skill_markdown, generate_mcp_config

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.post("/generate/{ontology_id}")
async def generate_mcp(ontology_id: str, request: Request, tenant_id: str = "default", db: AsyncSession = Depends(get_db)):
    ontology = await get_ontology(db, ontology_id, tenant_id=tenant_id)
    if not ontology:
        raise HTTPException(404, "Ontology not found")

    objects = await get_ontology_objects(db, ontology_id)
    obj_dicts = [{"name": o.name, "slug": o.slug, "description": o.description, "table_name": o.table_name} for o in objects]
    links = await get_ontology_links(db, ontology_id)
    link_dicts = [{"from_object": l.from_object, "to_object": l.to_object, "type": l.type, "from_column": l.from_column, "to_column": l.to_column} for l in links]
    funcs = await get_ontology_functions(db, ontology_id)
    func_dicts = [{"name": f.name, "handler": f.handler, "description": f.description} for f in funcs]

    tools = generate_tools(ontology_id, obj_dicts, link_dicts, func_dicts)
    base_url = str(request.base_url).rstrip("/")
    endpoint = f"{base_url}/mcp/{ontology.slug}"
    skill_data = generate_skill(ontology.name, ontology.slug, endpoint, tools)
    skill_md = generate_skill_markdown(skill_data)
    mcp_config = generate_mcp_config(ontology.slug, endpoint)

    return {
        "tools": tools,
        "tools_count": len(tools),
        "endpoint": endpoint,
        "skill": skill_data,
        "skill_markdown": skill_md,
        "mcp_config": mcp_config,
    }


@router.get("/servers")
async def list_servers(request: Request, tenant_id: str = "default", db: AsyncSession = Depends(get_db)):
    """List active MCP servers — one per ontology, all addressable via /mcp/{slug}."""
    from app.services.ontology.store import list_ontologies
    ontologies = await list_ontologies(db, tenant_id)
    base_url = str(request.base_url).rstrip("/")
    return {
        "servers": [
            {
                "id": o.id,
                "name": f"ontocenter-{o.slug}",
                "ontology_name": o.name,
                "ontology_slug": o.slug,
                "endpoint": f"{base_url}/mcp/{o.slug}",
                "status": "running",
            }
            for o in ontologies
        ]
    }


@router.get("/skills")
async def list_skills(tenant_id: str = "default", db: AsyncSession = Depends(get_db)):
    from app.services.ontology.store import list_ontologies
    ontologies = await list_ontologies(db, tenant_id)
    skills = []
    for o in ontologies:
        skills.append({
            "id": o.id,
            "ontology_id": o.id,
            "name": f"fin-{o.slug}",
            "version": "1.0.0",
            "description": f"{o.name} 数据查询能力",
            "ontology_name": o.name,
        })
    return {"skills": skills}
