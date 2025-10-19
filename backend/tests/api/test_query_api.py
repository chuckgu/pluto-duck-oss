from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from pluto_duck_backend.app.api.router import api_router
from pluto_duck_backend.app.services.execution import QueryExecutionService
from pluto_duck_backend.app.services.execution.manager import QueryExecutionManager


def create_app(warehouse: Path) -> FastAPI:
    app = FastAPI()

    service = QueryExecutionService(warehouse)
    manager = QueryExecutionManager(service)

    def override_service() -> QueryExecutionService:
        return service

    def override_manager() -> QueryExecutionManager:
        return manager

    app.dependency_overrides = {}
    from pluto_duck_backend.app.api.v1.query.router import get_execution_manager, get_execution_service

    app.dependency_overrides[get_execution_service] = override_service
    app.dependency_overrides[get_execution_manager] = override_manager
    app.include_router(api_router)
    return app


def test_submit_and_fetch_query(tmp_path):
    warehouse = tmp_path / "warehouse.duckdb"
    app = create_app(warehouse)
    client = TestClient(app)

    response = client.post("/api/v1/query", json={"sql": "select 1 as value"})
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    fetch_response = client.get(f"/api/v1/query/{job_id}")
    assert fetch_response.status_code == 200
    stream_response = client.get(f"/api/v1/query/{job_id}/events")
    assert stream_response.status_code == 200

