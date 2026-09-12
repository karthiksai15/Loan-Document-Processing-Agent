import uuid
from datetime import timedelta
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from fastapi import APIRouter, Depends, HTTPException

from app.main import app
from app.core.config import settings
from app.db.session import get_db, SessionLocal
from app.db.models import UserModel, LoanApplicationModel, ApplicantModel, HumanReviewModel
from app.services.auth_service import (
    create_access_token,
    decode_access_token,
    verify_google_id_token,
)
from app.api.deps import get_current_user, require_role, require_loan_officer, require_customer

client = TestClient(app)

# Helper test router to test role dependencies in isolation
mock_role_router = APIRouter(prefix="/test-roles")

@mock_role_router.get("/officer-only")
def officer_only_endpoint(user: UserModel = Depends(require_loan_officer)):
    return {"status": "ok", "user_id": user.id, "role": user.role}

@mock_role_router.get("/customer-only")
def customer_only_endpoint(user: UserModel = Depends(require_customer)):
    return {"status": "ok", "user_id": user.id, "role": user.role}

@mock_role_router.get("/either-role")
def either_role_endpoint(user: UserModel = Depends(require_role("CUSTOMER", "LOAN_OFFICER"))):
    return {"status": "ok", "user_id": user.id, "role": user.role}

app.include_router(mock_role_router)


# ---------------------------------------------------------------------------
# Unit tests: JWT creation, decoding, expiration, tampering
# ---------------------------------------------------------------------------

def test_jwt_create_and_decode():
    payload = {"sub": "usr_test123", "email": "officer@genbank.com", "role": "LOAN_OFFICER"}
    token = create_access_token(payload, expires_delta=timedelta(minutes=30))
    assert isinstance(token, str)
    assert len(token) > 20

    decoded = decode_access_token(token)
    assert decoded["sub"] == "usr_test123"
    assert decoded["email"] == "officer@genbank.com"
    assert decoded["role"] == "LOAN_OFFICER"
    assert "exp" in decoded
    assert "iat" in decoded


def test_jwt_expired_token_rejected():
    payload = {"sub": "usr_expired", "email": "expired@genbank.com", "role": "CUSTOMER"}
    expired_token = create_access_token(payload, expires_delta=timedelta(minutes=-5))

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(expired_token)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


def test_jwt_invalid_signature_rejected():
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("this.is.a.completely.invalid.token")
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Integration tests: Google OAuth endpoint (POST /api/v1/auth/google)
# ---------------------------------------------------------------------------

@patch("app.services.auth_service.google_id_token.verify_oauth2_token")
def test_google_auth_new_customer_registration(mock_verify):
    google_sub = f"google-sub-{uuid.uuid4().hex[:8]}"
    mock_email = f"borrower_{uuid.uuid4().hex[:6]}@example.com"
    mock_verify.return_value = {
        "sub": google_sub,
        "email": mock_email,
        "name": "Aarav Borrower",
        "picture": "https://lh3.googleusercontent.com/a/test",
        "email_verified": True,
        "aud": settings.GOOGLE_CLIENT_ID,
        "iss": "accounts.google.com"
    }

    resp = client.post("/api/v1/auth/google", json={"id_token": "mock-valid-google-id-token"})
    assert resp.status_code == 200
    data = resp.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == mock_email
    assert data["user"]["name"] == "Aarav Borrower"
    assert data["user"]["role"] == "CUSTOMER"
    assert data["user"]["picture_url"] == "https://lh3.googleusercontent.com/a/test"
    assert data["user"]["id"].startswith("usr_")


@patch("app.services.auth_service.google_id_token.verify_oauth2_token")
def test_google_auth_new_officer_with_role_preference(mock_verify):
    google_sub = f"google-sub-{uuid.uuid4().hex[:8]}"
    mock_email = f"staff_{uuid.uuid4().hex[:6]}@gmail.com"
    mock_verify.return_value = {
        "sub": google_sub,
        "email": mock_email,
        "name": "Team Staff Member",
        "picture": "https://lh3.googleusercontent.com/a/staff",
        "email_verified": True,
        "aud": settings.GOOGLE_CLIENT_ID,
        "iss": "https://accounts.google.com"
    }

    # 1. Any authenticated user selecting LOAN_OFFICER receives LOAN_OFFICER role without allowlist
    resp = client.post("/api/v1/auth/google", json={
        "id_token": "mock-officer-token",
        "role": "LOAN_OFFICER"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["role"] == "LOAN_OFFICER"
    assert data["user"]["email"] == mock_email

    # 1b. Any authenticated user selecting CUSTOMER receives CUSTOMER role
    google_sub_cust = f"google-sub-{uuid.uuid4().hex[:8]}"
    cust_email = f"borrower_{uuid.uuid4().hex[:6]}@gmail.com"
    mock_verify.return_value = {
        "sub": google_sub_cust,
        "email": cust_email,
        "name": "Customer Borrower",
        "picture": "https://lh3.googleusercontent.com/a/cust",
        "email_verified": True,
        "aud": settings.GOOGLE_CLIENT_ID,
        "iss": "https://accounts.google.com"
    }
    resp_cust = client.post("/api/v1/auth/google", json={
        "id_token": "mock-customer-token",
        "role": "CUSTOMER"
    })
    assert resp_cust.status_code == 200
    assert resp_cust.json()["user"]["role"] == "CUSTOMER"

    # 1c. When role preference is omitted, non-allowlisted email defaults to CUSTOMER
    google_sub_def = f"google-sub-{uuid.uuid4().hex[:8]}"
    def_email = f"default_{uuid.uuid4().hex[:6]}@gmail.com"
    mock_verify.return_value = {
        "sub": google_sub_def,
        "email": def_email,
        "name": "Default User",
        "email_verified": True,
        "aud": settings.GOOGLE_CLIENT_ID,
        "iss": "https://accounts.google.com"
    }
    resp_def = client.post("/api/v1/auth/google", json={
        "id_token": "mock-default-token"
    })
    assert resp_def.status_code == 200
    assert resp_def.json()["user"]["role"] == "CUSTOMER"


@patch("app.services.auth_service.google_id_token.verify_oauth2_token")
def test_google_auth_existing_user_login(mock_verify):
    google_sub = f"google-sub-{uuid.uuid4().hex[:8]}"
    mock_email = f"repeat_{uuid.uuid4().hex[:6]}@example.com"
    mock_verify.return_value = {
        "sub": google_sub,
        "email": mock_email,
        "name": "Repeat User",
        "picture": "https://example.com/pic1.jpg",
        "email_verified": True,
        "aud": settings.GOOGLE_CLIENT_ID,
        "iss": "accounts.google.com"
    }

    # 1. First login (creates user)
    resp1 = client.post("/api/v1/auth/google", json={"id_token": "mock-token-1"})
    assert resp1.status_code == 200
    user_id_1 = resp1.json()["user"]["id"]

    # 2. Second login with same Google account (logs into existing user)
    mock_verify.return_value["picture"] = "https://example.com/pic2_updated.jpg"
    resp2 = client.post("/api/v1/auth/google", json={"id_token": "mock-token-2"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["user"]["id"] == user_id_1
    assert data2["user"]["picture_url"] == "https://example.com/pic2_updated.jpg"


@patch("app.services.auth_service.google_id_token.verify_oauth2_token")
def test_google_auth_invalid_token_fails(mock_verify):
    mock_verify.side_effect = ValueError("Invalid token signature")

    resp = client.post("/api/v1/auth/google", json={"id_token": "forged-or-expired-token"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


@patch("app.services.auth_service.google_id_token.verify_oauth2_token")
def test_google_auth_audience_mismatch_fails(mock_verify):
    mock_verify.return_value = {
        "sub": "sub-wrong-aud",
        "email": "hacker@example.com",
        "email_verified": True,
        "aud": "wrong-client-id.apps.googleusercontent.com",
        "iss": "accounts.google.com"
    }

    resp = client.post("/api/v1/auth/google", json={"id_token": "token-wrong-audience"})
    assert resp.status_code == 401
    assert "audience" in resp.json()["detail"].lower()


@patch("app.services.auth_service.google_id_token.verify_oauth2_token")
def test_google_auth_unverified_email_fails(mock_verify):
    mock_verify.return_value = {
        "sub": "sub-unverified",
        "email": "unverified@example.com",
        "email_verified": False,
        "aud": settings.GOOGLE_CLIENT_ID,
        "iss": "accounts.google.com"
    }

    resp = client.post("/api/v1/auth/google", json={"id_token": "token-unverified-email"})
    assert resp.status_code == 401
    assert "not verified" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Integration tests: GET /api/v1/auth/me
# ---------------------------------------------------------------------------

@patch("app.services.auth_service.google_id_token.verify_oauth2_token")
def test_get_me_authenticated(mock_verify):
    google_sub = f"google-sub-{uuid.uuid4().hex[:8]}"
    mock_email = f"getme_{uuid.uuid4().hex[:6]}@example.com"
    mock_verify.return_value = {
        "sub": google_sub,
        "email": mock_email,
        "name": "GetMe User",
        "email_verified": True,
        "aud": settings.GOOGLE_CLIENT_ID,
        "iss": "accounts.google.com"
    }

    login_resp = client.post("/api/v1/auth/google", json={"id_token": "valid-token"})
    token = login_resp.json()["access_token"]
    user_id = login_resp.json()["user"]["id"]

    # Call /auth/me with valid Bearer token
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["id"] == user_id
    assert me_data["email"] == mock_email
    assert me_data["role"] == "CUSTOMER"


def test_get_me_missing_token():
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert "required" in resp.json()["detail"].lower()


def test_get_me_invalid_token():
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-jwt"})
    assert resp.status_code == 401


def test_get_me_expired_token():
    db = SessionLocal()
    try:
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        user = UserModel(
            id=user_id,
            email=f"expired_{uuid.uuid4().hex[:6]}@example.com",
            name="Expired User",
            google_id=f"gid_{uuid.uuid4().hex[:8]}",
            role="CUSTOMER"
        )
        db.add(user)
        db.commit()

        expired_token = create_access_token(
            {"sub": user.id, "email": user.email, "role": user.role},
            expires_delta=timedelta(minutes=-10)
        )
    finally:
        db.close()

    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Integration tests: Role-based access control (require_role)
# ---------------------------------------------------------------------------

def test_role_authorization_enforcement():
    db = SessionLocal()
    try:
        # Create a Loan Officer user
        officer = UserModel(
            id=f"usr_{uuid.uuid4().hex[:12]}",
            email=f"officer_{uuid.uuid4().hex[:6]}@genbank.com",
            name="Test Officer",
            google_id=f"gid_{uuid.uuid4().hex[:8]}",
            role="LOAN_OFFICER"
        )
        # Create a Customer user
        customer = UserModel(
            id=f"usr_{uuid.uuid4().hex[:12]}",
            email=f"customer_{uuid.uuid4().hex[:6]}@example.com",
            name="Test Customer",
            google_id=f"gid_{uuid.uuid4().hex[:8]}",
            role="CUSTOMER"
        )
        db.add_all([officer, customer])
        db.commit()

        officer_token = create_access_token({"sub": officer.id, "email": officer.email, "role": officer.role})
        customer_token = create_access_token({"sub": customer.id, "email": customer.email, "role": customer.role})
    finally:
        db.close()

    # 1. Officer accessing officer-only endpoint -> 200 OK
    resp = client.get("/test-roles/officer-only", headers={"Authorization": f"Bearer {officer_token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "LOAN_OFFICER"

    # 2. Customer accessing officer-only endpoint -> 403 Forbidden
    resp = client.get("/test-roles/officer-only", headers={"Authorization": f"Bearer {customer_token}"})
    assert resp.status_code == 403
    assert "required role: loan_officer" in resp.json()["detail"].lower()

    # 3. Customer accessing customer-only endpoint -> 200 OK
    resp = client.get("/test-roles/customer-only", headers={"Authorization": f"Bearer {customer_token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "CUSTOMER"

    # 4. Officer accessing customer-only endpoint -> 403 Forbidden
    resp = client.get("/test-roles/customer-only", headers={"Authorization": f"Bearer {officer_token}"})
    assert resp.status_code == 403

    # 5. Both accessing either-role endpoint -> 200 OK
    resp = client.get("/test-roles/either-role", headers={"Authorization": f"Bearer {officer_token}"})
    assert resp.status_code == 200
    resp = client.get("/test-roles/either-role", headers={"Authorization": f"Bearer {customer_token}"})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Phase 1 Step 5: Required Role & Access Verification Tests
# ---------------------------------------------------------------------------

@patch("app.services.auth_service.google_id_token.verify_oauth2_token")
def test_gmail_customer_login(mock_verify):
    """1. Gmail customer login -> CUSTOMER"""
    google_sub = f"g-sub-cust-{uuid.uuid4().hex[:8]}"
    email = f"borrower_{uuid.uuid4().hex[:6]}@gmail.com"
    mock_verify.return_value = {
        "sub": google_sub,
        "email": email,
        "name": "Arjun Kumar",
        "picture": "https://lh3.googleusercontent.com/a/cust",
        "email_verified": True,
        "aud": settings.GOOGLE_CLIENT_ID,
        "iss": "https://accounts.google.com"
    }

    resp = client.post("/api/v1/auth/google", json={
        "id_token": "token-cust",
        "role": "CUSTOMER"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["role"] == "CUSTOMER"
    assert data["user"]["email"] == email

    # Verify JWT role claim is CUSTOMER
    decoded = decode_access_token(data["access_token"])
    assert decoded["role"] == "CUSTOMER"

    # Verify database persistence
    db = SessionLocal()
    try:
        user_db = db.query(UserModel).filter(UserModel.id == data["user"]["id"]).first()
        assert user_db is not None
        assert user_db.role == "CUSTOMER"
    finally:
        db.close()


@patch("app.services.auth_service.google_id_token.verify_oauth2_token")
def test_gmail_staff_login(mock_verify):
    """2. Gmail staff login -> LOAN_OFFICER"""
    google_sub = f"g-sub-staff-{uuid.uuid4().hex[:8]}"
    email = f"officer_{uuid.uuid4().hex[:6]}@gmail.com"
    mock_verify.return_value = {
        "sub": google_sub,
        "email": email,
        "name": "Devi Raman",
        "picture": "https://lh3.googleusercontent.com/a/staff",
        "email_verified": True,
        "aud": settings.GOOGLE_CLIENT_ID,
        "iss": "https://accounts.google.com"
    }

    with patch.object(settings, "LOAN_OFFICER_EMAILS", email):
        resp = client.post("/api/v1/auth/google", json={
            "id_token": "token-staff",
            "role": "LOAN_OFFICER"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["role"] == "LOAN_OFFICER"
        assert data["user"]["email"] == email

        # Verify JWT role claim is LOAN_OFFICER
        decoded = decode_access_token(data["access_token"])
        assert decoded["role"] == "LOAN_OFFICER"

        # Verify database persistence
        db = SessionLocal()
        try:
            user_db = db.query(UserModel).filter(UserModel.id == data["user"]["id"]).first()
            assert user_db is not None
            assert user_db.role == "LOAN_OFFICER"
        finally:
            db.close()


@patch("app.services.auth_service.google_id_token.verify_oauth2_token")
def test_multiple_different_gmail_staff_accounts_see_all_applications(mock_verify):
    """3. Multiple different Gmail staff accounts -> all can see all applications"""
    app_1_id = f"TEST-APP-{uuid.uuid4().hex[:6]}"
    app_2_id = f"TEST-APP-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        app_1 = LoanApplicationModel(
            application_id=app_1_id,
            applicant_name="Applicant One",
            loan_amount=150000.0,
            status="PENDING"
        )
        app_2 = LoanApplicationModel(
            application_id=app_2_id,
            applicant_name="Applicant Two",
            loan_amount=250000.0,
            status="PENDING"
        )
        db.add_all([app_1, app_2])
        db.commit()
    finally:
        db.close()

    email_1 = f"team_lead_{uuid.uuid4().hex[:6]}@gmail.com"
    email_2 = f"reviewer_{uuid.uuid4().hex[:6]}@gmail.com"

    with patch.object(settings, "LOAN_OFFICER_EMAILS", f"{email_1},{email_2}"):
        # Staff 1 login
        mock_verify.return_value = {
            "sub": f"sub-{uuid.uuid4().hex[:8]}",
            "email": email_1,
            "name": "Team Lead",
            "email_verified": True,
            "aud": settings.GOOGLE_CLIENT_ID,
            "iss": "https://accounts.google.com"
        }
        resp1 = client.post("/api/v1/auth/google", json={"id_token": "tok1", "role": "LOAN_OFFICER"})
        tok1 = resp1.json()["access_token"]

        # Staff 2 login
        mock_verify.return_value = {
            "sub": f"sub-{uuid.uuid4().hex[:8]}",
            "email": email_2,
            "name": "Reviewer Staff",
            "email_verified": True,
            "aud": settings.GOOGLE_CLIENT_ID,
            "iss": "https://accounts.google.com"
        }
        resp2 = client.post("/api/v1/auth/google", json={"id_token": "tok2", "role": "LOAN_OFFICER"})
        tok2 = resp2.json()["access_token"]

    # Both staff can list applications and see all
    res_staff1 = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {tok1}"})
    assert res_staff1.status_code == 200
    app_ids_1 = [a["application_id"] for a in res_staff1.json()["applications"]]
    assert app_1_id in app_ids_1
    assert app_2_id in app_ids_1

    res_staff2 = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {tok2}"})
    assert res_staff2.status_code == 200
    app_ids_2 = [a["application_id"] for a in res_staff2.json()["applications"]]
    assert app_1_id in app_ids_2
    assert app_2_id in app_ids_2


def test_customer_a_cannot_see_customer_b_application():
    """4. Customer A cannot see Customer B's application"""
    db = SessionLocal()
    try:
        cust_a = UserModel(
            id=f"usr_{uuid.uuid4().hex[:12]}",
            email=f"cust_a_{uuid.uuid4().hex[:6]}@gmail.com",
            name="Customer A",
            google_id=f"gid_{uuid.uuid4().hex[:8]}",
            role="CUSTOMER"
        )
        cust_b = UserModel(
            id=f"usr_{uuid.uuid4().hex[:12]}",
            email=f"cust_b_{uuid.uuid4().hex[:6]}@gmail.com",
            name="Customer B",
            google_id=f"gid_{uuid.uuid4().hex[:8]}",
            role="CUSTOMER"
        )
        db.add_all([cust_a, cust_b])
        db.commit()

        app_b_id = f"APP-B-{uuid.uuid4().hex[:6]}"
        app_b = LoanApplicationModel(
            application_id=app_b_id,
            application_number=app_b_id,
            user_id=cust_b.id,
            applicant_name="Customer B",
            loan_amount=500000.0,
            status="DRAFT"
        )
        db.add(app_b)
        db.commit()

        token_a = create_access_token({"sub": cust_a.id, "email": cust_a.email, "role": cust_a.role})
    finally:
        db.close()

    # Customer A calls /customer/applications -> cannot see Customer B's application
    resp_list = client.get("/api/v1/customer/applications", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_list.status_code == 200
    my_ids = [a["application_id"] for a in resp_list.json()["applications"]]
    assert app_b_id not in my_ids

    # Customer A attempts to directly fetch Customer B's application -> 403 Forbidden
    resp_detail = client.get(f"/api/v1/customer/applications/{app_b_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_detail.status_code == 403
    assert "access denied" in resp_detail.json()["detail"].lower()


def test_customer_cannot_access_officer_apis():
    """5. Customer cannot access officer APIs"""
    app_id = f"TEST-APP-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        cust = UserModel(
            id=f"usr_{uuid.uuid4().hex[:12]}",
            email=f"cust_{uuid.uuid4().hex[:6]}@gmail.com",
            name="Customer User",
            google_id=f"gid_{uuid.uuid4().hex[:8]}",
            role="CUSTOMER"
        )
        test_app = LoanApplicationModel(
            application_id=app_id,
            applicant_name="Applicant",
            loan_amount=100000.0,
            status="PENDING"
        )
        db.add_all([cust, test_app])
        db.commit()
        cust_token = create_access_token({"sub": cust.id, "email": cust.email, "role": cust.role})
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {cust_token}"}

    # 1. Staff list applications -> 403
    r1 = client.get("/api/v1/applications", headers=headers)
    assert r1.status_code == 403
    assert "required role: loan_officer or manager" in r1.json()["detail"].lower()

    # 2. Staff dashboard overview -> 403
    r2 = client.get("/api/v1/applications/dashboard/overview", headers=headers)
    assert r2.status_code == 403

    # 3. Staff single application view -> 403
    r3 = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert r3.status_code == 403

    # 4. Human review decision -> 403
    r4 = client.post(f"/api/v1/applications/{app_id}/human-review/decision", json={
        "decision": "APPROVED",
        "officer_id": cust.id
    }, headers=headers)
    assert r4.status_code == 403

    # 5. Human review acknowledge -> 403
    r5 = client.post(f"/api/v1/applications/{app_id}/human-review/acknowledge", json={
        "officer_id": cust.id
    }, headers=headers)
    assert r5.status_code == 403

    # 6. Human review note -> 403
    r6 = client.post(f"/api/v1/applications/{app_id}/human-review/note", json={
        "note": "A note",
        "officer_id": cust.id
    }, headers=headers)
    assert r6.status_code == 403


def test_staff_can_access_all_applications():
    """6. Staff can access all applications and review endpoints"""
    app_id = f"TEST-APP-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        officer = UserModel(
            id=f"usr_{uuid.uuid4().hex[:12]}",
            email=f"officer_{uuid.uuid4().hex[:6]}@gmail.com",
            name="Bank Staff Officer",
            google_id=f"gid_{uuid.uuid4().hex[:8]}",
            role="LOAN_OFFICER"
        )
        app_item = LoanApplicationModel(
            application_id=app_id,
            applicant_name="Applicant Underwriting",
            loan_amount=750000.0,
            status="PENDING"
        )
        db.add_all([officer, app_item])
        db.commit()
        officer_token = create_access_token({"sub": officer.id, "email": officer.email, "role": officer.role})
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {officer_token}"}

    # 1. Staff can list all applications
    r1 = client.get("/api/v1/applications", headers=headers)
    assert r1.status_code == 200
    ids = [a["application_id"] for a in r1.json()["applications"]]
    assert app_id in ids

    # 2. Staff can get application details
    r2 = client.get(f"/api/v1/applications/{app_id}", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["application_id"] == app_id

    # 3. Staff can get dashboard overview
    r3 = client.get("/api/v1/applications/dashboard/overview", headers=headers)
    assert r3.status_code == 200

    # 4. Staff can access human-review gate
    r4 = client.get(f"/api/v1/applications/{app_id}/human-review", headers=headers)
    assert r4.status_code == 200


def test_no_hardcoded_officer_identity():
    """7. No hardcoded officer identity: review actions use authenticated user ID"""
    custom_officer_id = f"usr_dynamic_{uuid.uuid4().hex[:8]}"
    app_id = f"TEST-APP-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        officer = UserModel(
            id=custom_officer_id,
            email="dynamic_staff@gmail.com",
            name="Vikram Underwriter",
            google_id=f"gid_{uuid.uuid4().hex[:8]}",
            role="LOAN_OFFICER"
        )
        app_item = LoanApplicationModel(
            application_id=app_id,
            applicant_name="Dynamic Review Test",
            loan_amount=300000.0,
            status="PENDING"
        )
        db.add_all([officer, app_item])
        db.commit()
        token = create_access_token({"sub": officer.id, "email": officer.email, "role": officer.role})
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}

    # Add note without passing officer_id in body
    note_resp = client.post(
        f"/api/v1/applications/{app_id}/human-review/note",
        json={"note": "Verified KYC documents directly."},
        headers=headers
    )
    assert note_resp.status_code == 200
    data = note_resp.json()
    assert len(data["officer_notes"]) >= 1
    latest_note = data["officer_notes"][-1]
    # Verify officer_id is strictly the authenticated user's ID
    assert latest_note["officer_id"] == custom_officer_id
    assert latest_note["officer_id"] != "loan_officer_001"
    assert latest_note["officer_id"] != "Priya Sharma"

    # Check audit trail
    audit_resp = client.get(f"/api/v1/applications/{app_id}/human-review/audit", headers=headers)
    assert audit_resp.status_code == 200
    audit_events = audit_resp.json()["events"]
    assert any(ev["actor_id"] == custom_officer_id for ev in audit_events)
    assert all(ev["actor_id"] != "loan_officer_001" for ev in audit_events)
