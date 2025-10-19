"""Query API endpoints."""

from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from pluto_duck_backend.app.core.config import get_settings
from pluto_duck_backend.app.services.execution import QueryExecutionService
from pluto_duck_backend.app.services.execution.manager import (
    QueryExecutionManager,
    get_execution_manager,
)

router = APIRouter()


def get_execution_service() -> QueryExecutionService:
    settings = get_settings()
    return QueryExecutionService(settings.duckdb.path)


@router.post("", response_model=dict)
def submit_query(
    payload: dict,
    manager: QueryExecutionManager = Depends(get_execution_manager),
    service: QueryExecutionService = Depends(get_execution_service),
) -> dict:
    sql = payload.get("sql")
    if not sql:
        raise HTTPException(status_code=400, detail="sql field is required")
    job_id = manager.submit_sql(sql)
    job = manager.wait_for(job_id)
    if not job:
        raise HTTPException(status_code=500, detail="job missing")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "result_table": job.result_table,
    }


@router.get("/{job_id}", response_model=dict)
def get_query(job_id: str, service: QueryExecutionService = Depends(get_execution_service)) -> dict:
    job = service.fetch(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "result_table": job.result_table,
        "error": job.error,
    }


@router.get("/{job_id}/events")
def stream_query_events(
    job_id: str,
    manager: QueryExecutionManager = Depends(get_execution_manager),
) -> StreamingResponse:
    def event_stream():
        yield "data: " + json.dumps({"event": "started", "job_id": job_id}) + "\n\n"
        job = manager.wait_for(job_id)
        if job:
            payload = {
                "event": "completed",
                "job_id": job.job_id,
                "status": job.status,
                "result_table": job.result_table,
                "error": job.error,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
            yield "data: " + json.dumps(payload) + "\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

