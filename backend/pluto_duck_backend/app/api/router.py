"""FastAPI router wiring for Pluto-Duck backend."""

from fastapi import APIRouter

from .v1 import actions, dbt, ingest, query

api_router = APIRouter()
api_router.include_router(query.router, prefix="/api/v1/query", tags=["query"])
api_router.include_router(ingest.router, prefix="/api/v1/ingest", tags=["ingest"])
api_router.include_router(dbt.router, prefix="/api/v1/dbt", tags=["dbt"])
api_router.include_router(actions.router, prefix="/api/v1/actions", tags=["actions"])

