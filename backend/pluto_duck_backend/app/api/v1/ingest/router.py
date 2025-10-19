"""Ingestion endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from pluto_duck_backend.app.core.config import get_settings
from pluto_duck_backend.app.services.ingestion import IngestionJob, IngestionService, get_registry

router = APIRouter()


def get_ingestion_service() -> IngestionService:
    registry = get_registry()
    return IngestionService(registry)


@router.post("", response_model=dict)
def run_ingestion(payload: dict, service: IngestionService = Depends(get_ingestion_service)) -> dict:
    connector = payload.get("connector")
    target_table = payload.get("target_table")
    config = payload.get("config", {})
    overwrite = payload.get("overwrite", False)
    if not connector or not target_table:
        raise HTTPException(status_code=400, detail="connector and target_table are required")
    settings = get_settings()
    job = IngestionJob(
        connector=connector,
        target_table=target_table,
        warehouse_path=settings.duckdb.path,
        overwrite=overwrite,
        config=config,
    )
    result = service.run(job)
    response = {
        "connector": connector,
        "target_table": target_table,
        "rows_ingested": result.get("rows_ingested"),
        "metadata": result.get("metadata"),
    }
    return response

