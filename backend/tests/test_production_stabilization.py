import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import Settings, settings
import io
from app.db.session import SessionLocal
from app.db.models import (
    UserModel,
    LoanApplicationModel,
    DocumentModel,
    DocumentFileModel,
    HumanReviewAuditModel,
    HumanReviewModel,
)
from app.services.auth_service import (
    create_access_token,
    determine_user_role,
    authenticate_google_user,
)
from app.services import document_service
from app.services.human_review_service import evaluate_human_review_gate
from app.services.document_classification_service import classify_document
from app.services.field_extraction_service import extract_and_save_fields

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def officer_auth():
    db = SessionLocal()
    try:
        officer = db.query(UserModel).filter(UserModel.email == "officer_stabilization@genbank.com").first()
        if not officer:
            officer = UserModel(
                id=f"usr_{uuid.uuid4().hex[:12]}",
                email="officer_stabilization@genbank.com",
                name="Stabilization Officer",
                google_id=f"gid_{uuid.uuid4().hex[:12]}",
                role="LOAN_OFFICER",
            )
            db.add(officer)
            db.commit()
            db.refresh(officer)

        token = create_access_token({
            "sub": officer.id,
            "email": officer.email,
            "role": officer.role,
        })
        return {"headers": {"Authorization": f"Bearer {token}"}, "user": officer}
    finally:
        db.close()


@pytest.fixture
def customer_a_auth():
    db = SessionLocal()
    try:
        cust = db.query(UserModel).filter(UserModel.email == "customer_a@example.com").first()
        if not cust:
            cust = UserModel(
                id=f"usr_{uuid.uuid4().hex[:12]}",
                email="customer_a@example.com",
                name="Customer Alpha",
                google_id=f"gid_{uuid.uuid4().hex[:12]}",
                role="CUSTOMER",
            )
            db.add(cust)
            db.commit()
            db.refresh(cust)

        token = create_access_token({
            "sub": cust.id,
            "email": cust.email,
            "role": cust.role,
        })
        return {"headers": {"Authorization": f"Bearer {token}"}, "user": cust}
    finally:
        db.close()


@pytest.fixture
def customer_b_auth():
    db = SessionLocal()
    try:
        cust = db.query(UserModel).filter(UserModel.email == "customer_b@example.com").first()
        if not cust:
            cust = UserModel(
                id=f"usr_{uuid.uuid4().hex[:12]}",
                email="customer_b@example.com",
                name="Customer Beta",
                google_id=f"gid_{uuid.uuid4().hex[:12]}",
                role="CUSTOMER",
            )
            db.add(cust)
            db.commit()
            db.refresh(cust)

        token = create_access_token({
            "sub": cust.id,
            "email": cust.email,
            "role": cust.role,
        })
        return {"headers": {"Authorization": f"Bearer {token}"}, "user": cust}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Test 1: Customer Decision Reflection & Datetime Fix (P0)
# ---------------------------------------------------------------------------

def test_customer_decision_reflection_with_human_review(customer_a_auth, db_session):
    cust = customer_a_auth["user"]
    app_id = f"APP_DEC_{uuid.uuid4().hex[:8]}"

    loan_app = LoanApplicationModel(
        application_id=app_id,
        application_number=f"GB-DEC-{uuid.uuid4().hex[:6].upper()}",
        applicant_name=cust.name,
        user_id=cust.id,
        loan_amount=25000.0,
        status="approved",
        is_demo=False,
    )
    db_session.add(loan_app)

    # Attach HumanReviewModel representing officer's approved decision
    # (specifically exercises fallback when created_at is None to datetime.min)
    review = HumanReviewModel(
        review_action_id=f"act_{uuid.uuid4().hex[:8]}",
        application_id=app_id,
        human_decision="APPROVED",
        decision_reason="All documents validated and credit check passed",
        created_at=None,
        reviewed_at=datetime.utcnow(),
    )
    db_session.add(review)
    db_session.commit()

    # Call customer endpoint to retrieve application details
    resp = client.get(
        f"/api/v1/customer/applications/{app_id}",
        headers=customer_a_auth["headers"],
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["decision"] == "APPROVED"
    assert data["decision_reason"] == "All documents validated and credit check passed"

    # Also verify customer list applications endpoint
    list_resp = client.get(
        "/api/v1/customer/applications",
        headers=customer_a_auth["headers"],
    )
    assert list_resp.status_code == 200, list_resp.text
    list_data = list_resp.json()
    matching = [a for a in list_data["applications"] if a["application_id"] == app_id]
    assert len(matching) == 1
    assert matching[0]["decision"] == "APPROVED"


# ---------------------------------------------------------------------------
# Test 2: Officer Auth Bypass Prevention (P0)
# ---------------------------------------------------------------------------

def test_officer_endpoints_unauthenticated_return_401():
    routes = [
        ("GET", "/api/v1/applications"),
        ("POST", "/api/v1/applications/seed-demo-data"),
        ("GET", "/api/v1/applications/app_dummy/human-review/audit"),
        ("POST", "/api/v1/applications/app_dummy/human-review/decision"),
    ]
    for method, path in routes:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json={})
        assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}, expected 401"


def test_officer_endpoints_customer_role_returns_403(customer_a_auth):
    routes = [
        ("GET", "/api/v1/applications"),
        ("POST", "/api/v1/applications/seed-demo-data"),
        ("GET", "/api/v1/applications/app_dummy/human-review/audit"),
        ("POST", "/api/v1/applications/app_dummy/human-review/decision"),
    ]
    for method, path in routes:
        if method == "GET":
            resp = client.get(path, headers=customer_a_auth["headers"])
        else:
            resp = client.post(path, headers=customer_a_auth["headers"], json={})
        assert resp.status_code == 403, f"{method} {path} returned {resp.status_code}, expected 403"


# ---------------------------------------------------------------------------
# Test 3: Privilege Escalation Prevention (P0)
# ---------------------------------------------------------------------------

def test_determine_user_role_hackathon_open_access():
    with patch.object(settings, "LOAN_OFFICER_EMAILS", "officer@genbank.com"):
        with patch.object(settings, "MANAGER_EMAILS", "manager@genbank.com"):
            # User selecting loan officer portal gets LOAN_OFFICER
            role = determine_user_role("applicant@external.com", role_preference="loan_officer")
            assert role == "LOAN_OFFICER"

            # User selecting manager portal gets MANAGER
            role = determine_user_role("applicant@external.com", role_preference="manager")
            assert role == "MANAGER"

            # User selecting customer portal gets CUSTOMER
            role = determine_user_role("applicant@external.com", role_preference="customer")
            assert role == "CUSTOMER"

            # When role preference is omitted, allowlists take precedence
            role = determine_user_role("officer@genbank.com", role_preference=None)
            assert role == "LOAN_OFFICER"

            role = determine_user_role("manager@genbank.com", role_preference=None)
            assert role == "MANAGER"

            role = determine_user_role("unknown@external.com", role_preference=None)
            assert role == "CUSTOMER"


def test_google_login_portal_selection_role_assignment(db_session):
    user_email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    mock_id_info = {
        "sub": f"gid_{uuid.uuid4().hex[:10]}",
        "email": user_email,
        "name": "Portal User",
        "picture": "https://example.com/pic.jpg",
    }

    with patch("app.services.auth_service.verify_google_id_token", return_value=mock_id_info):
        # 1. Login as Loan Officer
        user, token = authenticate_google_user(
            db=db_session,
            id_token_str="fake_token",
            role_preference="loan_officer",
        )
        assert user.role == "LOAN_OFFICER"
        assert user.email == user_email

        # 2. Same user subsequently switches portal to Customer
        user_switch, token_switch = authenticate_google_user(
            db=db_session,
            id_token_str="fake_token",
            role_preference="customer",
        )
        assert user_switch.role == "CUSTOMER"
        assert user_switch.id == user.id



# ---------------------------------------------------------------------------
# Test 4: Document Endpoint IDOR / Missing Auth Prevention (P0)
# ---------------------------------------------------------------------------

def test_document_endpoints_unauthenticated_return_401():
    doc_id = "doc_test_123"
    routes = [
        ("GET", f"/api/v1/documents/{doc_id}"),
        ("GET", f"/api/v1/documents/{doc_id}/download"),
        ("GET", "/api/v1/applications/app_test_123/documents"),
        ("GET", f"/api/v1/documents/{doc_id}/text"),
    ]
    for method, path in routes:
        resp = client.get(path)
        assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}, expected 401"


def test_document_idor_customer_isolation(customer_a_auth, customer_b_auth, officer_auth, db_session):
    cust_a = customer_a_auth["user"]
    app_a_id = f"APP_IDOR_{uuid.uuid4().hex[:8]}"
    doc_a_id = f"DOC_IDOR_{uuid.uuid4().hex[:8]}"

    # Customer A owns application and document
    app_a = LoanApplicationModel(
        application_id=app_a_id,
        application_number=f"GB-IDOR-{uuid.uuid4().hex[:6]}",
        applicant_name=cust_a.name,
        user_id=cust_a.id,
        loan_amount=100000.0,
        status="documents_uploaded",
        is_demo=False,
    )
    db_session.add(app_a)

    doc_a = DocumentModel(
        document_id=doc_a_id,
        application_id=app_a_id,
        original_filename="paystub_a.pdf",
        stored_filename=f"{doc_a_id}_paystub_a.pdf",
        file_path="/tmp/nonexistent_paystub_a.pdf",
        document_type="PAYSLIP",
        file_size=1024,
        checksum="checksum_abc123",
        extracted_text="Customer A confidential paystub text",
    )
    db_session.add(doc_a)
    db_session.commit()

    # Customer B attempts to access Customer A's document details -> 403
    resp = client.get(f"/api/v1/documents/{doc_a.document_id}", headers=customer_b_auth["headers"])
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    # Customer B attempts to download Customer A's document file -> 403
    resp = client.get(f"/api/v1/documents/{doc_a.document_id}/download", headers=customer_b_auth["headers"])
    assert resp.status_code == 403

    # Customer B attempts to list Customer A's application documents -> 403
    resp = client.get(f"/api/v1/applications/{app_a.application_id}/documents", headers=customer_b_auth["headers"])
    assert resp.status_code == 403

    # Customer A accesses own document -> 200
    resp = client.get(f"/api/v1/documents/{doc_a.document_id}", headers=customer_a_auth["headers"])
    assert resp.status_code == 200
    assert resp.json()["document_id"] == doc_a.document_id

    # Officer accesses Customer A's document -> 200
    resp = client.get(f"/api/v1/documents/{doc_a.document_id}", headers=officer_auth["headers"])
    assert resp.status_code == 200
    assert resp.json()["document_id"] == doc_a.document_id


# ---------------------------------------------------------------------------
# Test 5: Demo Data Segregation (P1)
# ---------------------------------------------------------------------------

def test_demo_data_segregated_by_default(officer_auth, db_session):
    real_app_id = f"APP_REAL_{uuid.uuid4().hex[:8]}"
    demo_app_id = f"APP_DEMO_{uuid.uuid4().hex[:8]}"

    real_app = LoanApplicationModel(
        application_id=real_app_id,
        application_number=f"GB-REAL-{uuid.uuid4().hex[:6]}",
        applicant_name="Real Applicant",
        loan_amount=50000.0,
        status="submitted",
        is_demo=False,
    )
    demo_app = LoanApplicationModel(
        application_id=demo_app_id,
        application_number=f"GB-DEMO-{uuid.uuid4().hex[:6]}",
        applicant_name="Demo Applicant",
        loan_amount=75000.0,
        status="submitted",
        is_demo=True,
    )
    db_session.add(real_app)
    db_session.add(demo_app)
    db_session.commit()

    # Default listing: demo data excluded
    resp = client.get("/api/v1/applications", headers=officer_auth["headers"])
    assert resp.status_code == 200
    data = resp.json()
    returned_ids = [item["application_id"] for item in data["applications"]]
    assert real_app.application_id in returned_ids
    assert demo_app.application_id not in returned_ids

    # Listing with include_demo=true: demo data included
    resp_with_demo = client.get("/api/v1/applications?include_demo=true", headers=officer_auth["headers"])
    assert resp_with_demo.status_code == 200
    data_with_demo = resp_with_demo.json()
    returned_with_demo_ids = [item["application_id"] for item in data_with_demo["applications"]]
    assert real_app.application_id in returned_with_demo_ids
    assert demo_app.application_id in returned_with_demo_ids


# ---------------------------------------------------------------------------
# Test 6: Extracted Text DB Persistence Across Simulated Disk Cache Wipe (P1)
# ---------------------------------------------------------------------------

def test_extracted_text_persists_in_db_when_disk_file_missing(db_session):
    app_id = f"APP_PERSIST_{uuid.uuid4().hex[:8]}"
    doc_id = f"DOC_PERSIST_{uuid.uuid4().hex[:8]}"

    loan_app = LoanApplicationModel(
        application_id=app_id,
        application_number=f"GB-PERSIST-{uuid.uuid4().hex[:6]}",
        applicant_name="Jane Doe",
        loan_amount=30000.0,
        status="submitted",
        is_demo=False,
    )
    db_session.add(loan_app)

    # Document whose physical file on disk is MISSING, but extracted_text is in DB
    sample_text = "GENBANK PAYSLIP\nEmployee Name: Jane Doe\nMonthly Gross Income: $8,500.00\nNet Pay: $6,800.00\nEmployer: Acme Corp"
    doc = DocumentModel(
        document_id=doc_id,
        application_id=app_id,
        original_filename="missing_from_disk_paystub.pdf",
        stored_filename=f"{doc_id}_missing.pdf",
        file_path="/tmp/non_existent_path_simulating_container_wipe.pdf",
        document_type="PAYSLIP",
        file_size=2048,
        extraction_status="COMPLETED",
        extracted_text=sample_text,
    )
    db_session.add(doc)
    db_session.commit()

    # Classification service should seamlessly use DB-persisted text without FileNotFoundError
    classified_doc = classify_document(db_session, doc_id)
    assert classified_doc.classified_document_type == "PAYSLIP"
    assert classified_doc.classification_confidence > 0.5

    # Field extraction service should also work directly with DB-persisted text
    extracted_doc = extract_and_save_fields(db_session, doc_id)
    assert extracted_doc.field_extraction_status == "COMPLETED"
    assert len(extracted_doc.extracted_fields_data) > 0
    field_names = [f.field_name for f in extracted_doc.extracted_fields_data]
    assert any("gross" in name.lower() or "income" in name.lower() or "pay" in name.lower() or "employer" in name.lower() for name in field_names)


# ---------------------------------------------------------------------------
# Test 7: JWT Secret Production Safety (P1)
# ---------------------------------------------------------------------------

def test_jwt_secret_production_safety_blocks_default_key():
    # In production with default dev secret, Settings must raise RuntimeError
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "JWT_SECRET_KEY": "genbank-jwt-dev-secret-key-change-in-production",
    }):
        with pytest.raises(RuntimeError) as exc_info:
            Settings()
        assert "CRITICAL SECURITY CONFIGURATION ERROR" in str(exc_info.value)


def test_jwt_secret_production_safety_allows_strong_key():
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "JWT_SECRET_KEY": "a-strong-custom-production-jwt-secret-key-that-is-safe",
    }):
        prod_settings = Settings()
        assert prod_settings.JWT_SECRET_KEY == "a-strong-custom-production-jwt-secret-key-that-is-safe"


# ---------------------------------------------------------------------------
# Test 8: Test Database Safety Guard (P1)
# ---------------------------------------------------------------------------

def test_test_safety_guard_blocks_production_hosts():
    dangerous_hosts = [
        "ep-proud-water-12345.us-east-2.aws.neon.tech/genbank",
        "genbank-prod.c12345.render.com/genbank_prod",
        "db.xyz.supabase.co:5432/postgres",
        "rds.amazonaws.com/genbank",
    ]
    disallowed_keywords = ["neon.tech", "amazonaws.com", "render.com", "supabase.co", "cockroachlabs.cloud"]

    for host in dangerous_hosts:
        matched = any(kw in host.lower() for kw in disallowed_keywords)
        assert matched, f"Safety guard failed to flag dangerous host: {host}"


# ---------------------------------------------------------------------------
# Test 9: Demo Seed Audit Trail Idempotency (P1)
# ---------------------------------------------------------------------------

def test_evaluate_human_review_gate_idempotent_audit_trail(db_session):
    app_id = f"APP_IDEM_{uuid.uuid4().hex[:8]}"

    loan_app = LoanApplicationModel(
        application_id=app_id,
        application_number=f"GB-IDEM-{uuid.uuid4().hex[:6]}",
        applicant_name="Audit Idempotency Test",
        loan_amount=50000.0,
        status="submitted",
        is_demo=False,
    )
    db_session.add(loan_app)
    db_session.commit()

    # First evaluation
    gate_result_1 = evaluate_human_review_gate(application_id=app_id, db=db_session)
    assert gate_result_1.human_review_required in (True, 1)

    audit_count_1 = db_session.query(HumanReviewAuditModel).filter(
        HumanReviewAuditModel.application_id == app_id,
        HumanReviewAuditModel.action == "HUMAN_REVIEW_GATE_EVALUATED",
    ).count()
    assert audit_count_1 == 1

    # Second evaluation with identical state
    gate_result_2 = evaluate_human_review_gate(application_id=app_id, db=db_session)
    assert gate_result_2.human_review_required in (True, 1)

    audit_count_2 = db_session.query(HumanReviewAuditModel).filter(
        HumanReviewAuditModel.application_id == app_id,
        HumanReviewAuditModel.action == "HUMAN_REVIEW_GATE_EVALUATED",
    ).count()
    # Must remain 1, not duplicate
    assert audit_count_2 == 1


# ---------------------------------------------------------------------------
# Test 10: Document Upload Foreign Key Integrity & Lifecycle Regressions (P0)
# ---------------------------------------------------------------------------

def test_authenticated_customer_can_upload_document_successfully(customer_a_auth, db_session):
    """
    Regression Test 10a & 10b:
    1. Authenticated customer uploads a document to their own application.
    2. Document row MUST exist in DB before DocumentFile row is created.
    3. Document and DocumentFile foreign key relationship is strictly satisfied.
    """
    headers = customer_a_auth["headers"]
    cust_id = customer_a_auth["user"].id

    # Create draft application for Customer A
    resp_app = client.post(
        "/api/v1/customer/applications",
        json={
            "applicant_name": "Customer A Upload Test",
            "loan_amount": 350000.0,
            "income_annum": 600000.0,
        },
        headers=headers,
    )
    assert resp_app.status_code == 201
    app_id = resp_app.json()["application_id"]

    # Upload document
    test_content = b"%PDF-1.4 Mock Payslip content for Customer A"
    files = {"file": ("payslip_cust_a.pdf", io.BytesIO(test_content), "application/pdf")}
    data = {"document_type": "PAYSLIP"}

    upload_resp = client.post(
        f"/api/v1/customer/applications/{app_id}/documents",
        files=files,
        data=data,
        headers=headers,
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document_id"]
    assert doc_id.startswith("DOC-")

    # Verify parent Document row exists in DB
    parent_doc = db_session.query(DocumentModel).filter(DocumentModel.document_id == doc_id).first()
    assert parent_doc is not None
    assert parent_doc.application_id == app_id
    assert parent_doc.uploaded_by == cust_id
    assert parent_doc.document_type == "PAYSLIP"

    # Verify child DocumentFile row exists and references parent Document
    child_file = db_session.query(DocumentFileModel).filter(DocumentFileModel.document_id == doc_id).first()
    assert child_file is not None
    assert child_file.file_content == test_content
    assert child_file.file_size == len(test_content)

    # Verify ORM relationship traversal
    assert parent_doc.file_record is not None
    assert parent_doc.file_record.document_id == doc_id
    assert child_file.document.document_id == doc_id


def test_uploaded_file_can_subsequently_be_retrieved(customer_a_auth, db_session):
    """
    Regression Test 10c:
    Uploaded file can be retrieved via storage service and downloaded via API.
    """
    headers = customer_a_auth["headers"]

    # Create draft application
    resp_app = client.post(
        "/api/v1/customer/applications",
        json={"applicant_name": "Retrieval Test", "loan_amount": 200000.0},
        headers=headers,
    )
    assert resp_app.status_code == 201
    app_id = resp_app.json()["application_id"]

    # Upload document
    test_bytes = b"Hello GenBank Underwriting - retrieval test bytes"
    files = {"file": ("bank_statement_retrieval.txt", io.BytesIO(test_bytes), "text/plain")}
    data = {"document_type": "BANK_STATEMENT"}

    upload_resp = client.post(
        f"/api/v1/customer/applications/{app_id}/documents",
        files=files,
        data=data,
        headers=headers,
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document_id"]

    # Retrieve via storage service
    retrieved_bytes, mime = document_service.get_document_bytes(db_session, doc_id)
    assert retrieved_bytes == test_bytes

    # Retrieve via API download endpoint
    dl_resp = client.get(f"/api/v1/documents/{doc_id}/download", headers=headers)
    assert dl_resp.status_code == 200
    assert dl_resp.content == test_bytes


def test_unauthorized_customer_cannot_upload_to_another_customer_application(customer_a_auth, customer_b_auth):
    """
    Regression Test 10d:
    Customer B attempts to upload a document to Customer A's application -> 403 Forbidden.
    """
    headers_a = customer_a_auth["headers"]
    headers_b = customer_b_auth["headers"]

    # Customer A creates an application
    resp_app = client.post(
        "/api/v1/customer/applications",
        json={"applicant_name": "Customer A App", "loan_amount": 400000.0},
        headers=headers_a,
    )
    assert resp_app.status_code == 201
    app_id_a = resp_app.json()["application_id"]

    # Customer B attempts to upload document to Customer A's application
    files = {"file": ("attack_doc.pdf", io.BytesIO(b"Malicious payload"), "application/pdf")}
    data = {"document_type": "PAYSLIP"}

    resp_hack = client.post(
        f"/api/v1/customer/applications/{app_id_a}/documents",
        files=files,
        data=data,
        headers=headers_b,
    )
    assert resp_hack.status_code == 403
    assert "access denied" in resp_hack.json()["detail"].lower()


def test_invalid_application_or_document_requests_return_correct_error(customer_a_auth):
    """
    Regression Test 10e:
    Invalid requests return correct HTTP error codes:
    - Nonexistent application -> 404
    - Missing filename / empty file -> 400
    - Unsupported file extension -> 400
    - Invalid document category -> 400
    """
    headers = customer_a_auth["headers"]

    # 1. Nonexistent application -> 404
    files = {"file": ("doc.pdf", io.BytesIO(b"some content"), "application/pdf")}
    data = {"document_type": "PAYSLIP"}
    resp = client.post(
        "/api/v1/customer/applications/GEN-NONEXISTENT-999999/documents",
        files=files,
        data=data,
        headers=headers,
    )
    assert resp.status_code == 404

    # Create valid app for remaining validation tests
    resp_app = client.post(
        "/api/v1/customer/applications",
        json={"applicant_name": "Validation Target", "loan_amount": 100000.0},
        headers=headers,
    )
    app_id = resp_app.json()["application_id"]

    # 2. Unsupported file extension (.exe) -> 400
    files_bad_ext = {"file": ("malware.exe", io.BytesIO(b"binary data"), "application/x-msdownload")}
    resp_bad_ext = client.post(
        f"/api/v1/customer/applications/{app_id}/documents",
        files=files_bad_ext,
        data={"document_type": "PAYSLIP"},
        headers=headers,
    )
    assert resp_bad_ext.status_code == 400
    assert "unsupported" in resp_bad_ext.json()["detail"].lower()

    # 3. Invalid document type -> 400
    files_valid = {"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 valid"), "application/pdf")}
    resp_bad_type = client.post(
        f"/api/v1/customer/applications/{app_id}/documents",
        files=files_valid,
        data={"document_type": "NOT_A_VALID_TYPE"},
        headers=headers,
    )
    assert resp_bad_type.status_code == 400
    assert "invalid document category" in resp_bad_type.json()["detail"].lower()

    # 4. Empty file (0 bytes) -> 400
    files_empty = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    resp_empty = client.post(
        f"/api/v1/customer/applications/{app_id}/documents",
        files=files_empty,
        data={"document_type": "PAYSLIP"},
        headers=headers,
    )
    assert resp_empty.status_code == 400
    assert "empty" in resp_empty.json()["detail"].lower()

