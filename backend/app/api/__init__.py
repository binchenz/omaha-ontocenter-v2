"""
API package.
"""
from fastapi import APIRouter
from app.api import auth, projects, datahub, ontology, query, assets, chat, api_keys, semantic, watchlist, datasources, members, audit, pipelines, agent, ontology_store_routes

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(datahub.router, prefix="/datahub", tags=["datahub"])
api_router.include_router(ontology.router, prefix="/ontology", tags=["ontology"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(api_keys.router, prefix="/projects", tags=["api-keys"])
api_router.include_router(semantic.router, prefix="", tags=["semantic"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
api_router.include_router(datasources.router, tags=["datasources"])
api_router.include_router(members.router, tags=["members"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(pipelines.router, tags=["pipelines"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(ontology_store_routes.router, prefix="/ontology-store", tags=["ontology-store"])
