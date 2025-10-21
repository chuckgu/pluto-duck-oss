"""Agent API endpoints for LangGraph orchestration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from pluto_duck_backend.agent.core.orchestrator import (
    AgentRunManager,
    get_agent_manager,
    safe_dump_event,
)


router = APIRouter()


def get_manager() -> AgentRunManager:
    return get_agent_manager()


@router.post("/run", status_code=status.HTTP_202_ACCEPTED, response_model=dict)
async def start_agent_run(payload: dict, manager: AgentRunManager = Depends(get_manager)) -> dict:
    question = payload.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    conversation_id, run_id = manager.start_run(question)
    return {
        "conversation_id": conversation_id,
        "run_id": run_id,
        "events_url": f"/api/v1/agent/{run_id}/events",
    }


@router.get("/{run_id}", response_model=dict)
async def get_agent_result(run_id: str, manager: AgentRunManager = Depends(get_manager)) -> dict:
    try:
        result = await manager.get_result(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    return result


@router.get("/{run_id}/events")
async def stream_agent_events(run_id: str, request: Request, manager: AgentRunManager = Depends(get_manager)) -> StreamingResponse:
    try:
        # Ensure the run exists before starting the stream
        _ = manager._runs[run_id]  # type: ignore[attr-defined]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc

    event_stream = manager.stream_events(run_id)

    async def generator():
        async for event in event_stream:
            if await request.is_disconnected():
                break
            yield safe_dump_event(event)

    return StreamingResponse(generator(), media_type="text/event-stream")


