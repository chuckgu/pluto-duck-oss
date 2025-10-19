from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from pluto_duck_backend.app.api.router import api_router


def create_app(warehouse: Path) -> FastAPI:
    app = FastAPI()

    from pluto_duck_backend.app.api.v1.dbt.router import get_dbt_service

    class FakeDbtService:
        def run(self, select=None, vars=None):
            return {"status": "success", "select": select, "vars": vars}

        def test(self, select=None):
            return {"status": "success", "select": select}

    app.dependency_overrides[get_dbt_service] = lambda: FakeDbtService()
    app.include_router(api_router)
    return app


def test_dbt_run_endpoint(tmp_path: Path, monkeypatch) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    app = create_app(warehouse)
    client = TestClient(app)

    response = client.post("/api/v1/dbt/run", json={})
    assert response.status_code == 200

