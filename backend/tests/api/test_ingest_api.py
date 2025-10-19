from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from pluto_duck_backend.app.api.router import api_router
from pluto_duck_backend.app.services.ingestion import IngestionService, IngestionJob, get_registry


def create_app(warehouse: Path) -> FastAPI:
    app = FastAPI()

    from pluto_duck_backend.app.api.v1.ingest.router import get_ingestion_service

    def override_ingestion_service() -> IngestionService:
        service = IngestionService(get_registry())

        def run_with_override(job: IngestionJob) -> dict:
            job.warehouse_path = warehouse
            return original_run(job)

        original_run = service.run
        service.run = run_with_override  # type: ignore[assignment]
        return service

    app.dependency_overrides[get_ingestion_service] = override_ingestion_service
    app.include_router(api_router)
    return app


def test_ingest_endpoint(tmp_path: Path, monkeypatch) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    app = create_app(warehouse)
    client = TestClient(app)

    payload = {
        "connector": "csv",
        "target_table": "people",
        "config": {"path": str(tmp_path / "data.csv")},
    }

    (tmp_path / "data.csv").write_text("id,name\n1,Alice\n", encoding="utf-8")

    response = client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 200

