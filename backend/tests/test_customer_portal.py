import io
import os
import uuid
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.db.models import UserModel, LoanApplicationModel, DocumentFileModel
from app.services.auth_service import create_access_token
from app.services.customer_service import generate_application_number
from app.services import document_service

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def customer_user(db_session: Session):
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    user = UserModel(
        id=user_id,
        email=f"customer_{uuid.uuid4().hex[:6]}@example.com",
        name="Aarav Customer",
        google_id=f"gid_{uuid.uuid4().hex[:8]}",
        role="CUSTOMER",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return {"user": user, "token": token}


@pytest.fixture
def other_customer_user(db_session: Session):
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    user = UserModel(
        id=user_id,
        email=f"other_{uuid.uuid4().hex[:6]}@example.com",
        name="Other Customer",
        google_id=f"gid_{uuid.uuid4().hex[:8]}",
        role="CUSTOMER",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return {"user": user, "token": token}


@pytest.fixture
def officer_user(db_session: Session):
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    user = UserModel(
        id=user_id,
        email=f"officer_{uuid.uuid4().hex[:6]}@genbank.com",
        name="Priya Loan Officer",
        google_id=f"gid_{uuid.uuid4().hex[:8]}",
        role="LOAN_OFFICER",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return {"user": user, "token": token}


# ---------------------------------------------------------------------------
# 1. Application Number Generation Tests
# ---------------------------------------------------------------------------

def test_application_number_format(db_session: Session):
    current_year = datetime.now().year
    app_num_1 = generate_application_number(db_session)
    assert app_num_1.startswith(f"GEN-{current_year}-")
    seq_part_1 = app_num_1.split("-")[-1]
    assert len(seq_part_1) == 6
    assert seq_part_1.isdigit()

    # Create dummy app with app_num_1 to ensure next is incremented
    app_id = f"APP_{uuid.uuid4().hex[:8]}"
    dummy = LoanApplicationModel(
        application_id=app_id,
        application_number=app_num_1,
        applicant_name="Test Applicant",
        loan_amount=500000.0,
        status="DRAFT",
    )
    db_session.add(dummy)
    db_session.commit()

    app_num_2 = generate_application_number(db_session)
    seq_part_2 = app_num_2.split("-")[-1]
    assert int(seq_part_2) == int(seq_part_1) + 1


# ---------------------------------------------------------------------------
# 2. Customer Application Creation & Listing Tests
# ---------------------------------------------------------------------------

def test_create_customer_application_success(customer_user):
    token = customer_user["token"]
    user = customer_user["user"]

    payload = {
        "applicant_name": "Rohan Verma",
        "loan_amount": 750000.0,
        "income_annum": 1020000.0,
        "employer": "Infosys Ltd",
        "loan_term": 36,
        "date_of_birth": "1990-05-15",
        "address": "123 Indiranagar, Bangalore, Karnataka 560038",
        "education": "Graduate",
        "self_employed": "No",
        "notes": "Home Renovation loan"
    }

    resp = client.post(
        "/api/v1/customer/applications",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 201
    data = resp.json()

    assert data["application_number"].startswith("GEN-")
    assert data["status"] == "DRAFT"
    assert data["loan_amount"] == 750000.0
    assert data["applicant_name"] == "Rohan Verma"
    assert data["documents_count"] == 0


def test_customer_applications_listing_and_isolation(customer_user, other_customer_user):
    cust_token = customer_user["token"]
    other_token = other_customer_user["token"]

    # Customer 1 creates an application
    resp1 = client.post(
        "/api/v1/customer/applications",
        json={
            "applicant_name": "Customer One",
            "loan_amount": 300000.0,
            "income_annum": 540000.0,
        },
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert resp1.status_code == 201
    app1_id = resp1.json()["application_id"]

    # Customer 2 lists applications - should be empty for them
    resp_list_other = client.get(
        "/api/v1/customer/applications",
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert resp_list_other.status_code == 200
    other_apps = resp_list_other.json()["applications"]
    assert not any(a["application_id"] == app1_id for a in other_apps)

    # Customer 2 tries to GET Customer 1's application -> 403 Forbidden
    resp_get_other = client.get(
        f"/api/v1/customer/applications/{app1_id}",
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert resp_get_other.status_code == 403

    # Customer 1 can get their own application
    resp_get_own = client.get(
        f"/api/v1/customer/applications/{app1_id}",
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert resp_get_own.status_code == 200
    assert resp_get_own.json()["application_id"] == app1_id


# ---------------------------------------------------------------------------
# 3. Persistent Document Upload & Storage Recovery Tests
# ---------------------------------------------------------------------------

def test_customer_document_upload_and_persistence(customer_user, db_session: Session):
    token = customer_user["token"]

    # Create application
    resp_app = client.post(
        "/api/v1/customer/applications",
        json={
            "applicant_name": "Pooja Sharma",
            "loan_amount": 500000.0,
            "income_annum": 720000.0,
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp_app.status_code == 201
    app_id = resp_app.json()["application_id"]

    # Upload a document
    file_bytes = b"%PDF-1.4 Mock Payslip content for durable storage testing"
    files = {"file": ("payslip_march.pdf", io.BytesIO(file_bytes), "application/pdf")}
    data = {"document_type": "PAYSLIP"}

    upload_resp = client.post(
        f"/api/v1/customer/applications/{app_id}/documents",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    doc_id = doc_data["document_id"]
    assert doc_data["document_type"] == "PAYSLIP"
    assert doc_data["original_filename"] == "payslip_march.pdf"

    # Verify binary persistence in database
    db_file = db_session.query(DocumentFileModel).filter(DocumentFileModel.document_id == doc_id).first()
    assert db_file is not None
    assert db_file.file_content == file_bytes
    assert db_file.file_size == len(file_bytes)

    # Test disk cache deletion and automatic restoration from DB
    file_info = document_service.get_document_file_path(db_session, doc_id)
    assert file_info is not None
    disk_path = file_info[0]
    assert os.path.exists(disk_path)

    # Simulate ephemeral disk wipe
    os.remove(disk_path)
    assert not os.path.exists(disk_path)

    # Calling get_document_file_path should restore it from DB
    restored_info = document_service.get_document_file_path(db_session, doc_id)
    assert restored_info is not None
    assert os.path.exists(restored_info[0])
    with open(restored_info[0], "rb") as f:
        assert f.read() == file_bytes


# ---------------------------------------------------------------------------
# 4. Customer Submission & Pipeline Trigger Tests
# ---------------------------------------------------------------------------

def test_customer_submit_application(customer_user):
    token = customer_user["token"]

    resp_app = client.post(
        "/api/v1/customer/applications",
        json={
            "applicant_name": "Suresh Patel",
            "loan_amount": 400000.0,
            "income_annum": 600000.0,
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp_app.status_code == 201
    app_id = resp_app.json()["application_id"]

    # Upload at least one document
    file_bytes = b"Bank statement content"
    files = {"file": ("statement.pdf", io.BytesIO(file_bytes), "application/pdf")}
    client.post(
        f"/api/v1/customer/applications/{app_id}/documents",
        files=files,
        data={"document_type": "BANK_STATEMENT"},
        headers={"Authorization": f"Bearer {token}"}
    )

    # Submit application
    submit_resp = client.post(
        f"/api/v1/customer/applications/{app_id}/submit",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert submit_resp.status_code == 200
    submit_data = submit_resp.json()
    assert submit_data["status"] == "SUBMITTED"

    # Verify that status is now SUBMITTED in detail endpoint
    get_resp = client.get(
        f"/api/v1/customer/applications/{app_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_resp.json()["status"] == "SUBMITTED"


# ---------------------------------------------------------------------------
# 5. Role-Based Access Control on Officer Actions
# ---------------------------------------------------------------------------

def test_customer_cannot_perform_officer_review(customer_user, officer_user):
    cust_token = customer_user["token"]
    off_token = officer_user["token"]

    # Create & submit customer application
    resp_app = client.post(
        "/api/v1/customer/applications",
        json={
            "applicant_name": "Kavita Reddy",
            "loan_amount": 350000.0,
            "income_annum": 660000.0,
        },
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert resp_app.status_code == 201
    app_id = resp_app.json()["application_id"]

    # Customer tries to record human decision -> 403 Forbidden
    decision_payload = {
        "decision": "APPROVED",
        "officer_id": "officer_fake",
        "notes": "Unauthorized customer approval attempt"
    }
    cust_dec_resp = client.post(
        f"/api/v1/applications/{app_id}/human-review/decision",
        json=decision_payload,
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert cust_dec_resp.status_code == 403

    # Officer can record note on the customer application
    note_payload = {
        "note": "Officer reviewing application documentation.",
        "officer_id": officer_user["user"].id
    }
    off_note_resp = client.post(
        f"/api/v1/applications/{app_id}/human-review/note",
        json=note_payload,
        headers={"Authorization": f"Bearer {off_token}"}
    )
    assert off_note_resp.status_code == 200


# ---------------------------------------------------------------------------
# 6. Officer Access to Customer Applications & Demo Apps
# ---------------------------------------------------------------------------

def test_officer_view_customer_app_by_number(customer_user):
    cust_token = customer_user["token"]

    resp_app = client.post(
        "/api/v1/customer/applications",
        json={
            "applicant_name": "Vikram Malhotra",
            "loan_amount": 900000.0,
            "income_annum": 1440000.0,
        },
        headers={"Authorization": f"Bearer {cust_token}"}
    )
    assert resp_app.status_code == 201
    app_num = resp_app.json()["application_number"]

    # Officer can lookup via application_number
    get_by_num = client.get(f"/api/v1/applications/{app_num}")
    assert get_by_num.status_code == 200
    assert get_by_num.json()["application_number"] == app_num

    # Demo cases (e.g. A001) remain accessible
    client.post("/api/v1/applications", json={"application_id": "A001", "applicant_name": "Aarav Sharma", "loan_amount": 1000000.0})
    get_demo = client.get("/api/v1/applications/A001")
    assert get_demo.status_code == 200
    assert get_demo.json()["applicant_name"] == "Aarav Sharma"
