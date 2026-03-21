"""Integration tests for the CodeCouncil API server."""
import pytest
from fastapi.testclient import TestClient

from codecouncil.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_list_runs_empty(client):
    response = client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data


def test_get_config(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "council" in data
    assert "llm" in data


def test_config_masks_secrets(client):
    response = client.get("/api/config")
    data = response.json()
    # API keys should be masked
    providers = data.get("llm", {}).get("providers", {})
    for name, prov in providers.items():
        if "api_key" in prov:
            assert prov["api_key"] == "" or prov["api_key"] == "***"


def test_list_agents(client):
    response = client.get("/api/agents")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data


def test_list_providers(client):
    response = client.get("/api/providers")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data


def test_list_personas(client):
    response = client.get("/api/personas")
    assert response.status_code == 200


def test_list_sessions(client):
    response = client.get("/api/sessions")
    assert response.status_code == 200


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "codecouncil" in response.text


def test_create_run_validation(client):
    # Missing repo_url should fail
    response = client.post("/api/runs", json={})
    assert response.status_code == 422


def test_get_nonexistent_run(client):
    response = client.get("/api/runs/nonexistent-id")
    assert response.status_code == 404
