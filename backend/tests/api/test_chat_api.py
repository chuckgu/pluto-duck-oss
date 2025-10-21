from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from pluto_duck_backend.app.api.router import api_router
from pluto_duck_backend.agent.core.orchestrator import get_agent_manager


def make_client() -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(api_router)
    return TestClient(app)


@pytest.fixture
def client() -> TestClient:
    return make_client()


def test_multi_turn_conversation(client: TestClient) -> None:
    question = "hello"
    create_response = client.post("/api/v1/chat/sessions", json={"question": question})
    assert create_response.status_code == 201
    created = create_response.json()
    conversation_id = created["id"]
    run_id_first = created["run_id"]

    detail_first = client.get(f"/api/v1/chat/sessions/{conversation_id}?include_events=true")
    assert detail_first.status_code == 200
    body_first = detail_first.json()
    assert body_first["run_id"] == run_id_first
    assert any(event["type"] == "run" for event in body_first.get("events", []))

    followup_payload = {"role": "user", "content": {"text": "next"}}
    followup_response = client.post(
        f"/api/v1/chat/sessions/{conversation_id}/messages",
        json=followup_payload,
    )
    assert followup_response.status_code == 202
    followup = followup_response.json()
    run_id_second = followup["run_id"]
    assert run_id_second is not None
    assert run_id_second != run_id_first

    detail_second = client.get(f"/api/v1/chat/sessions/{conversation_id}?include_events=true")
    assert detail_second.status_code == 200
    body_second = detail_second.json()
    assert body_second["run_id"] == run_id_second
    assert len(body_second["messages"]) >= len(body_first["messages"]) + 1

