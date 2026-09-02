import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_fleet_endpoint():
    response = client.get("/api/v1/fleet")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "clusters" in data
    assert "nodes" in data
    assert "cpu" in data
    assert "memory" in data
    assert "alerts" in data
    assert "status" in data


def test_clusters_endpoint():
    response = client.get("/api/v1/clusters")
    assert response.status_code == 200
    data = response.json()
    assert "clusters" in data
    assert isinstance(data["clusters"], list)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "thanos_connected" in data
    assert "clusters_discovered" in data
    assert "metrics_available" in data
    assert "metrics_unavailable" in data


def test_alerts_endpoint():
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert isinstance(data["alerts"], list)


def test_nonexistent_cluster():
    response = client.get("/api/v1/clusters/nonexistent")
    assert response.status_code == 404
