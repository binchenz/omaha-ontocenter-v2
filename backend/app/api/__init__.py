"""
API package.
"""
from fastapi import APIRouter
from app.api import auth, projects, datahub, ontology, query, assets

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(datahub.router, prefix="/datahub", tags=["datahub"])
api_router.include_router(ontology.router, prefix="/ontology", tags=["ontology"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
