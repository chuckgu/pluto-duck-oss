from fastapi import FastAPI
from fastapi.testclient import TestClient

from pluto_duck_backend.app.api.router import api_router


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(api_router)
    return app


def test_list_actions():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/actions")
    assert response.status_code == 200
    payload = response.json()
    assert "actions" in payload

