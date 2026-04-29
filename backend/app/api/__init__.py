"""
API package.
"""
from fastapi import APIRouter

from app.api.auth import login, api_keys
from app.api.projects import crud as projects_crud, members, assets, audit
from app.api.chat import chat
from app.api.ontology import store as ontology_store, legacy as ontology_legacy, semantic
from app.api.pipelines import crud as pipelines_crud
from app.api.legacy.financial import query, datasources, datahub, watchlist

api_router = APIRouter()

api_router.include_router(login.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects_crud.router, prefix="/projects", tags=["projects"])
api_router.include_router(datahub.router, prefix="/datahub", tags=["datahub"])
api_router.include_router(ontology_legacy.router, prefix="/ontology", tags=["ontology"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(api_keys.router, prefix="/projects", tags=["api-keys"])
api_router.include_router(semantic.router, prefix="", tags=["semantic"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
api_router.include_router(datasources.router, tags=["datasources"])
api_router.include_router(members.router, tags=["members"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(pipelines_crud.router, tags=["pipelines"])
api_router.include_router(ontology_store.router, prefix="/ontology-store", tags=["ontology-store"])
