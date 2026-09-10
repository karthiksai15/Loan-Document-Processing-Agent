import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_application():
    payload = {
        "application_id": "TEST-APP-001",
        "applicant_name": "John Doe",
        "loan_amount": 500000.0
    }
    response = client.post("/api/v1/applications", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["application_id"] == "TEST-APP-001"
    assert data["applicant_name"] == "John Doe"
    assert data["loan_amount"] == 500000.0
    assert data["status"] == "PENDING"
    assert data["documents_count"] == 0

def test_create_duplicate_application_fails():
    payload = {
        "application_id": "TEST-APP-001",
        "applicant_name": "John Doe Copy",
        "loan_amount": 100000.0
    }
    response = client.post("/api/v1/applications", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_get_application():
    response = client.get("/api/v1/applications/TEST-APP-001")
    assert response.status_code == 200
    data = response.json()
    assert data["application_id"] == "TEST-APP-001"

def test_get_nonexistent_application_404():
    response = client.get("/api/v1/applications/NONEXISTENT-APP-999")
    assert response.status_code == 404

def test_list_applications():
    response = client.get("/api/v1/applications")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(a["application_id"] == "TEST-APP-001" for a in data["applications"])
