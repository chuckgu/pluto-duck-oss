"""dbt API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from pluto_duck_backend.app.core.config import get_settings
from pluto_duck_backend.app.services.transformation import DbtService

router = APIRouter()


def get_dbt_service() -> DbtService:
    settings = get_settings()
    return DbtService(
        settings.dbt.project_path,
        settings.dbt.profiles_path,
        settings.data_dir.artifacts / "dbt",
        settings.duckdb.path,
    )


@router.post("/run", response_model=dict)
def dbt_run(payload: dict = None, service: DbtService = Depends(get_dbt_service)) -> dict:
    payload = payload or {}
    select = payload.get("select")
    vars_payload = payload.get("vars")
    result = service.run(select=select, vars=vars_payload)
    return {
        "status": "success",
        "run_id": result.get("run_id"),
        "generated_at": result.get("generated_at"),
        "artifacts_path": result.get("artifacts_path"),
        "models": result.get("models"),
    }


@router.post("/test", response_model=dict)
def dbt_test(payload: dict = None, service: DbtService = Depends(get_dbt_service)) -> dict:
    payload = payload or {}
    select = payload.get("select")
    result = service.test(select=select)
    return {
        "status": "success",
        "run_id": result.get("run_id"),
        "generated_at": result.get("generated_at"),
        "artifacts_path": result.get("artifacts_path"),
        "models": result.get("models"),
    }

