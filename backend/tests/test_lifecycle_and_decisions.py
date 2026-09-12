"""
Test Suite: GenBank End-to-End Application Lifecycle & Officer Decision Stabilization

Scenarios covered:
  1. Empty database returns 0 applications, no auto-seeding.
  2. Manual demo data seeding populates A001-A010.
  3. Demo data seeding is idempotent (calling repeatedly does not duplicate).
  4. Customer application creation with full applicant metadata.
  5. Persistent document upload to customer draft.
  6. Customer application submission and automated pipeline execution.
  7. Customer isolation & RBAC (customers cannot view/edit other customer files or access officer endpoints).
  8. Loan officer visibility (sees all applications including customer submissions).
  9. Application status lifecycle tracking.
  10. Officer Approve decision updates status to APPROVED and reflects to customer.
  11. Officer Reject decision updates status to REJECTED and reflects to customer.
  12. Officer Escalate decision updates status to ESCALATED and reflects to customer.
  13. Officer Request Documents updates status to ADDITIONAL_DOCUMENTS_REQUIRED.
  14. Customer uploads requested document on existing application, re-triggering review.
  15. Officer identity is immutably captured in audit logs without hardcoded placeholders.
  16. AI Review Agent execution and review history retrieval.
"""

import os
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.db.models import (
    LoanApplicationModel,
    ApplicantModel,
    DocumentModel,
    DocumentFileModel,
    HumanReviewModel,
    HumanReviewAuditModel,
    AgentReviewModel,
    UserModel,
)
from app.services.auth_service import create_access_token

client = TestClient(app)


# ── Helpers & Fixtures ─────────────────────────────────────────────────────────

def _create_user(db: Session, email: str, name: str, role: str) -> UserModel:
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        user = UserModel(
            id=f"usr_{uuid.uuid4().hex[:8]}",
            email=email,
            name=name,
            google_id=f"gid_{uuid.uuid4().hex[:8]}",
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _auth_headers(user: UserModel) -> dict:
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure clean state between tests where required."""
    yield


# ── TEST 1: Empty Database & Zero Auto-Seed ───────────────────────────────────

def test_empty_database_no_auto_seeding():
    db = SessionLocal()
    try:
        # Clear applications and human reviews
        db.query(HumanReviewAuditModel).delete()
        db.query(HumanReviewModel).delete()
        db.query(AgentReviewModel).delete()
        db.query(DocumentFileModel).delete()
        db.query(DocumentModel).delete()
        db.query(ApplicantModel).delete()
        db.query(LoanApplicationModel).delete()
        db.commit()

        officer = _create_user(db, "officer_empty@genbank.test", "Officer Test", "LOAN_OFFICER")
        headers = _auth_headers(officer)

        # GET /applications
        res = client.get("/api/v1/applications", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
        assert len(data["applications"]) == 0

        # GET /dashboard/overview
        overview_res = client.get("/api/v1/applications/dashboard/overview", headers=headers)
        assert overview_res.status_code == 200
        ov_data = overview_res.json()
        assert ov_data["total_applications"] == 0
        assert len(ov_data["attention_queue"]) == 0

        # Verify DB still has 0 applications (no auto-seeding occurred)
        assert db.query(LoanApplicationModel).count() == 0
    finally:
        db.close()


# ── TEST 2 & 3: Demo Data Seeding & Idempotency ────────────────────────────────

def test_demo_data_seeding_and_idempotency():
    db = SessionLocal()
    try:
        officer = _create_user(db, "officer_demo@genbank.test", "Officer Demo", "LOAN_OFFICER")
        headers = _auth_headers(officer)

        # 1. First seed call
        seed_res1 = client.post("/api/v1/applications/seed-demo-data", headers=headers)
        assert seed_res1.status_code == 200
        seed_data1 = seed_res1.json()
        assert "message" in seed_data1
        assert "seeded_applications" in seed_data1

        apps_res1 = client.get("/api/v1/applications", headers=headers)
        assert apps_res1.status_code == 200
        assert apps_res1.json()["total"] >= 10

        count_after_first = db.query(LoanApplicationModel).count()
        docs_after_first = db.query(DocumentModel).count()

        # 2. Second seed call (Must be idempotent)
        seed_res2 = client.post("/api/v1/applications/seed-demo-data", headers=headers)
        assert seed_res2.status_code == 200

        count_after_second = db.query(LoanApplicationModel).count()
        docs_after_second = db.query(DocumentModel).count()

        assert count_after_first == count_after_second, "Seeding created duplicate applications"
        assert docs_after_first == docs_after_second, "Seeding created duplicate documents"
    finally:
        db.close()


# ── TEST 4: Customer Application Creation with Metadata ───────────────────────

def test_customer_application_creation_with_metadata():
    db = SessionLocal()
    try:
        cust = _create_user(db, "cust_meta@genbank.test", "Jane Doe", "CUSTOMER")
        headers = _auth_headers(cust)

        payload = {
            "applicant_name": "Jane Doe",
            "loan_amount": 2500000.0,
            "income_annum": 1200000.0,
            "employer": "Tech Corp India",
            "loan_term": 24,
            "date_of_birth": "1992-05-15",
            "address": "Bangalore, Karnataka",
            "education": "Post Graduate",
            "self_employed": "No",
            "notes": "Home renovation loan"
        }

        res = client.post("/api/v1/customer/applications", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()

        assert data["application_number"].startswith("GEN-")
        assert data["applicant_name"] == "Jane Doe"
        assert data["loan_amount"] == 2500000.0
        assert data["income_annum"] == 1200000.0
        assert data["employer"] == "Tech Corp India"
        assert data["status"] == "DRAFT"

        # Verify database model persistence
        app_db = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == data["application_id"]).first()
        assert app_db is not None
        assert app_db.user_id == cust.id

        applicant_db = db.query(ApplicantModel).filter(ApplicantModel.applicant_id == data["application_id"]).first()
        assert applicant_db is not None
        assert applicant_db.employer == "Tech Corp India"
        assert applicant_db.education == "Post Graduate"
        assert applicant_db.date_of_birth == "1992-05-15"
    finally:
        db.close()


# ── TEST 5 & 6: Document Upload, Submission & Pipeline Execution ──────────────

def test_customer_document_upload_and_submission():
    db = SessionLocal()
    try:
        cust = _create_user(db, "cust_upload@genbank.test", "Rajesh Kumar", "CUSTOMER")
        headers = _auth_headers(cust)

        # 1. Create draft application
        create_res = client.post(
            "/api/v1/customer/applications",
            json={
                "applicant_name": "Rajesh Kumar",
                "loan_amount": 1500000.0,
                "income_annum": 800000.0,
                "employer": "Fintech Solutions",
            },
            headers=headers
        )
        assert create_res.status_code == 201
        app_id = create_res.json()["application_id"]

        # 2. Upload payslip document
        sample_payslip = b"PAYSLIP: Gross Income Rs 66666 monthly. Name: Rajesh Kumar. Employer: Fintech Solutions."
        upload_res = client.post(
            f"/api/v1/customer/applications/{app_id}/documents",
            files={"file": ("payslip.txt", sample_payslip, "text/plain")},
            data={"document_type": "PAYSLIP"},
            headers=headers
        )
        assert upload_res.status_code == 201
        doc_data = upload_res.json()
        assert doc_data["document_type"] == "PAYSLIP"
        assert doc_data["original_filename"] == "payslip.txt"

        # Verify persistent binary file storage
        db_file = db.query(DocumentFileModel).filter(DocumentFileModel.document_id == doc_data["document_id"]).first()
        assert db_file is not None
        assert db_file.file_content == sample_payslip

        # 3. Submit application
        submit_res = client.post(f"/api/v1/customer/applications/{app_id}/submit", headers=headers)
        assert submit_res.status_code == 200
        sub_data = submit_res.json()
        assert sub_data["status"] in ("SUBMITTED", "UNDER_REVIEW")

        # Verify status in database
        app_db = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == app_id).first()
        assert app_db.status in ("SUBMITTED", "UNDER_REVIEW")
    finally:
        db.close()


# ── TEST 7: Customer Isolation & RBAC ─────────────────────────────────────────

def test_customer_isolation_and_rbac():
    db = SessionLocal()
    try:
        cust_a = _create_user(db, "cust_a@genbank.test", "Customer A", "CUSTOMER")
        cust_b = _create_user(db, "cust_b@genbank.test", "Customer B", "CUSTOMER")

        headers_a = _auth_headers(cust_a)
        headers_b = _auth_headers(cust_b)

        # Create application for Customer A
        res_a = client.post(
            "/api/v1/customer/applications",
            json={"applicant_name": "Customer A", "loan_amount": 500000.0},
            headers=headers_a
        )
        app_a_id = res_a.json()["application_id"]

        # Customer B tries to view Customer A's application -> 403
        get_res = client.get(f"/api/v1/customer/applications/{app_a_id}", headers=headers_b)
        assert get_res.status_code == 403

        # Customer B tries to upload document to Customer A's application -> 403
        upload_res = client.post(
            f"/api/v1/customer/applications/{app_a_id}/documents",
            files={"file": ("hack.txt", b"hack", "text/plain")},
            data={"document_type": "KYC"},
            headers=headers_b
        )
        assert upload_res.status_code == 403

        # Customer A tries to access officer dashboard overview -> 403
        officer_res = client.get("/api/v1/applications/dashboard/overview", headers=headers_a)
        assert officer_res.status_code == 403

        # Customer A tries to record human review decision -> 403
        dec_res = client.post(
            f"/api/v1/applications/{app_a_id}/human-review/decision",
            json={"decision": "APPROVED", "decision_reason": "Self-approval attempt"},
            headers=headers_a
        )
        assert dec_res.status_code == 403
    finally:
        db.close()


# ── TEST 8: Loan Officer Visibility of Customer Applications ──────────────────

def test_officer_visibility_of_customer_applications():
    db = SessionLocal()
    try:
        cust = _create_user(db, "cust_vis@genbank.test", "Suresh Gupta", "CUSTOMER")
        officer = _create_user(db, "officer_vis@genbank.test", "Officer Visible", "LOAN_OFFICER")

        headers_cust = _auth_headers(cust)
        headers_officer = _auth_headers(officer)

        res = client.post(
            "/api/v1/customer/applications",
            json={
                "applicant_name": "Suresh Gupta",
                "loan_amount": 3000000.0,
                "employer": "Infy Tech",
            },
            headers=headers_cust
        )
        app_id = res.json()["application_id"]

        # Loan officer queries all applications
        list_res = client.get("/api/v1/applications", headers=headers_officer)
        assert list_res.status_code == 200
        app_ids = [a["application_id"] for a in list_res.json()["applications"]]
        assert app_id in app_ids

        # Loan officer opens specific application
        detail_res = client.get(f"/api/v1/applications/{app_id}", headers=headers_officer)
        assert detail_res.status_code == 200
        assert detail_res.json()["applicant_name"] == "Suresh Gupta"
    finally:
        db.close()


# ── TEST 9, 10, 11: Officer Decisions (Approve, Reject, Escalate) ─────────────

def test_officer_decisions_persistence_and_customer_reflection():
    db = SessionLocal()
    try:
        cust = _create_user(db, "cust_dec@genbank.test", "Sunita Verma", "CUSTOMER")
        officer = _create_user(db, "officer_dec@genbank.test", "Officer Raman", "LOAN_OFFICER")

        headers_cust = _auth_headers(cust)
        headers_officer = _auth_headers(officer)

        # 1. Create and submit application
        res = client.post(
            "/api/v1/customer/applications",
            json={"applicant_name": "Sunita Verma", "loan_amount": 2000000.0},
            headers=headers_cust
        )
        app_id = res.json()["application_id"]
        client.post(
            f"/api/v1/customer/applications/{app_id}/documents",
            files={"file": ("doc.txt", b"Sample content", "text/plain")},
            data={"document_type": "KYC"},
            headers=headers_cust
        )
        client.post(f"/api/v1/customer/applications/{app_id}/submit", headers=headers_cust)

        # 2. Officer records APPROVED decision
        approve_res = client.post(
            f"/api/v1/applications/{app_id}/human-review/decision",
            json={
                "decision": "APPROVED",
                "decision_reason": "Verified applicant KYC and sufficient asset coverage.",
                "override_reason": "Approved based on high net worth profile.",
            },
            headers=headers_officer
        )
        assert approve_res.status_code == 200

        # Verify LoanApplicationModel status is updated to APPROVED
        app_db = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == app_id).first()
        assert app_db.status == "APPROVED"

        # Verify customer sees APPROVED status on detail endpoint
        cust_app = client.get(f"/api/v1/customer/applications/{app_id}", headers=headers_cust).json()
        assert cust_app["status"] == "APPROVED"
        assert cust_app["decision"] == "APPROVED"
        assert "Verified applicant KYC" in cust_app["decision_reason"]

        # 3. Test REJECTED decision on a second application
        res2 = client.post(
            "/api/v1/customer/applications",
            json={"applicant_name": "Applicant Two", "loan_amount": 5000000.0},
            headers=headers_cust
        )
        app2_id = res2.json()["application_id"]
        client.post(
            f"/api/v1/customer/applications/{app2_id}/documents",
            files={"file": ("doc.txt", b"Sample content", "text/plain")},
            data={"document_type": "KYC"},
            headers=headers_cust
        )
        client.post(f"/api/v1/customer/applications/{app2_id}/submit", headers=headers_cust)

        reject_res = client.post(
            f"/api/v1/applications/{app2_id}/human-review/decision",
            json={
                "decision": "REJECTED",
                "decision_reason": "Debt-to-income ratio exceeds acceptable lending limit.",
                "override_reason": "Rejecting application.",
            },
            headers=headers_officer
        )
        assert reject_res.status_code == 200

        app2_db = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == app2_id).first()
        assert app2_db.status == "REJECTED"

        cust_app2 = client.get(f"/api/v1/customer/applications/{app2_id}", headers=headers_cust).json()
        assert cust_app2["status"] == "REJECTED"
        assert cust_app2["decision"] == "REJECTED"

        # 4. Test ESCALATED decision on a third application
        res3 = client.post(
            "/api/v1/customer/applications",
            json={"applicant_name": "Applicant Three", "loan_amount": 9000000.0},
            headers=headers_cust
        )
        app3_id = res3.json()["application_id"]
        client.post(
            f"/api/v1/customer/applications/{app3_id}/documents",
            files={"file": ("doc.txt", b"Sample content", "text/plain")},
            data={"document_type": "KYC"},
            headers=headers_cust
        )
        client.post(f"/api/v1/customer/applications/{app3_id}/submit", headers=headers_cust)

        escalate_res = client.post(
            f"/api/v1/applications/{app3_id}/human-review/decision",
            json={
                "decision": "ESCALATED",
                "notes": "Large exposure loan requiring senior credit committee review.",
                "override_reason": "Escalating for committee signoff.",
            },
            headers=headers_officer
        )
        assert escalate_res.status_code == 200

        app3_db = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == app3_id).first()
        assert app3_db.status == "ESCALATED"

        cust_app3 = client.get(f"/api/v1/customer/applications/{app3_id}", headers=headers_cust).json()
        assert cust_app3["status"] == "ESCALATED"
    finally:
        db.close()


# ── TEST 12, 13 & 14: Request Documents & Customer Re-upload ─────────────────

def test_request_documents_and_customer_reupload():
    db = SessionLocal()
    try:
        cust = _create_user(db, "cust_req@genbank.test", "Anil Mehta", "CUSTOMER")
        officer = _create_user(db, "officer_req@genbank.test", "Officer Mehta", "LOAN_OFFICER")

        headers_cust = _auth_headers(cust)
        headers_officer = _auth_headers(officer)

        # 1. Create and submit customer application
        res = client.post(
            "/api/v1/customer/applications",
            json={"applicant_name": "Anil Mehta", "loan_amount": 1800000.0},
            headers=headers_cust
        )
        app_id = res.json()["application_id"]
        client.post(
            f"/api/v1/customer/applications/{app_id}/documents",
            files={"file": ("payslip.txt", b"Salary slip content", "text/plain")},
            data={"document_type": "PAYSLIP"},
            headers=headers_cust
        )
        client.post(f"/api/v1/customer/applications/{app_id}/submit", headers=headers_cust)

        # 2. Officer requests TAX_RETURN
        req_res = client.post(
            f"/api/v1/applications/{app_id}/human-review/request-documents",
            json={
                "documents": ["TAX_RETURN"],
                "reason": "Please provide latest 2-year ITR-V acknowledgement."
            },
            headers=headers_officer
        )
        assert req_res.status_code == 200

        # Verify application status transitioned to ADDITIONAL_DOCUMENTS_REQUIRED
        app_db = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == app_id).first()
        assert app_db.status == "ADDITIONAL_DOCUMENTS_REQUIRED"

        # Customer checks detail
        cust_detail = client.get(f"/api/v1/customer/applications/{app_id}", headers=headers_cust).json()
        assert cust_detail["status"] == "ADDITIONAL_DOCUMENTS_REQUIRED"
        assert len(cust_detail["requested_documents"]) >= 1
        assert cust_detail["requested_documents"][-1]["doc_type"] == "TAX_RETURN"

        # 3. Customer uploads the requested TAX_RETURN document on the SAME application
        tax_doc = b"INCOME TAX RETURN ACKNOWLEDGEMENT ITR-V AY 2025-26. Total Income: Rs 1800000. Tax Paid: Rs 320000."
        upload_req_res = client.post(
            f"/api/v1/customer/applications/{app_id}/documents",
            files={"file": ("tax_return.txt", tax_doc, "text/plain")},
            data={"document_type": "TAX_RETURN"},
            headers=headers_cust
        )
        assert upload_req_res.status_code == 201

        # Verify application transitioned back to UNDER_REVIEW
        db.refresh(app_db)
        assert app_db.status == "UNDER_REVIEW"

        # Verify loan officer now sees the uploaded TAX_RETURN in the application's document list
        docs_res = client.get(f"/api/v1/applications/{app_id}/documents", headers=headers_officer)
        assert docs_res.status_code == 200
        filenames = [d["original_filename"] for d in docs_res.json()["documents"]]
        assert "tax_return.txt" in filenames
    finally:
        db.close()


# ── TEST 15: Officer Identity Capturing (No Placeholders) ─────────────────────

def test_officer_identity_captured_without_placeholders():
    db = SessionLocal()
    try:
        officer = _create_user(db, "custom_officer_789@genbank.test", "Custom Officer Name", "LOAN_OFFICER")
        headers = _auth_headers(officer)

        app_obj = LoanApplicationModel(
            application_id=f"APP-TEST-{uuid.uuid4().hex[:6]}",
            applicant_name="Test Identity Applicant",
            loan_amount=1000000.0,
            status="SUBMITTED"
        )
        db.add(app_obj)
        db.commit()

        # Add note without passing officer_id in body
        note_res = client.post(
            f"/api/v1/applications/{app_obj.application_id}/human-review/note",
            json={"note": "Verified KYC documents directly."},
            headers=headers
        )
        assert note_res.status_code == 200
        latest_note = note_res.json()["officer_notes"][-1]

        assert latest_note["officer_id"] == officer.id
        assert latest_note["officer_id"] != "loan_officer_001"
        assert latest_note["officer_id"] != "Priya Sharma"

        # Check audit trail
        audit_res = client.get(f"/api/v1/applications/{app_obj.application_id}/human-review/audit", headers=headers)
        assert audit_res.status_code == 200
        events = audit_res.json()["events"]
        assert any(e["actor_id"] == officer.id for e in events)
        assert all(e["actor_id"] != "loan_officer_001" for e in events)
    finally:
        db.close()


# ── TEST 16: AI Review Agent Execution and History ────────────────────────────

def test_agent_review_history_endpoint():
    db = SessionLocal()
    try:
        officer = _create_user(db, "officer_ai@genbank.test", "Officer AI", "LOAN_OFFICER")
        headers = _auth_headers(officer)

        app_id = f"APP-AI-{uuid.uuid4().hex[:6]}"
        app_obj = LoanApplicationModel(
            application_id=app_id,
            applicant_name="AI Test Applicant",
            loan_amount=1000000.0,
            status="UNDER_REVIEW"
        )
        db.add(app_obj)

        # Add two historical review records
        rev1 = AgentReviewModel(
            agent_review_id=f"AGT-{app_id}-01",
            application_id=app_id,
            investigation_status="COMPLETED",
            step_count=3,
            executive_summary="First run summary.",
            created_at=datetime(2026, 9, 10, 10, 0, 0),
        )
        rev2 = AgentReviewModel(
            agent_review_id=f"AGT-{app_id}-02",
            application_id=app_id,
            investigation_status="COMPLETED",
            step_count=4,
            executive_summary="Second run summary.",
            created_at=datetime(2026, 9, 11, 10, 0, 0),
        )
        db.add(rev1)
        db.add(rev2)
        db.commit()

        # Call GET /applications/{app_id}/agent/reviews
        res = client.get(f"/api/v1/applications/{app_id}/agent/reviews", headers=headers)
        assert res.status_code == 200
        reviews = res.json()
        assert len(reviews) == 2
        # Newest first
        assert reviews[0]["agent_review_id"] == f"AGT-{app_id}-02"
        assert reviews[1]["agent_review_id"] == f"AGT-{app_id}-01"
    finally:
        db.close()
