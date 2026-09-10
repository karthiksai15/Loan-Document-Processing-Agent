import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Welcome to Loan Document Processing Agent API" in data["message"]

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "project" in data

def test_system_info_endpoint():
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_statistics"]["total_demo_applicants"] == 10
    assert data["dataset_statistics"]["total_synthetic_documents"] == 38
