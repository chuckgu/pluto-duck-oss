"""Tests for the backend health endpoint."""

from fastapi.testclient import TestClient

from pluto_duck_backend.app.main import create_app


def test_health_endpoint_returns_ok_status() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "version" in payload
    assert "provider" in payload

