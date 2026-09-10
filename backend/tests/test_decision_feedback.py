"""
Phase 19 — Decision + Feedback Tests

Tests cover:
  1. Human decision is stored.
  2. AI recommendation is preserved.
  3. Human decision is preserved separately from AI recommendation.
  4. Aligned decision is detected (alignment_status == "ALIGNED").
  5. Override is detected (alignment_status == "OVERRIDDEN").
  6. Existing override reason requirement still works.
  7. Decision reason is stored (and required for APPROVED and REJECTED).
  8. Officer feedback is stored (text and optional category).
  9. Decision history API returns complete history.
  10. Cross-applicant isolation works.
  11. Invalid application returns 404.
  12. Demo applications (A001, A003, A006) verify correctly.
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import HumanReviewModel, HumanReviewAuditModel
from app.db.session import SessionLocal

client = TestClient(app)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _create_app(app_id: str, loan_amount: float = 1_000_000.0, applicant_name: str = None):
    res = client.post("/api/v1/applications", json={
        "application_id": app_id,
        "applicant_name": applicant_name or f"Test Applicant {app_id}",
        "loan_amount": loan_amount,
    })
    assert res.status_code in (201, 400, 409), f"Create app failed: {res.text}"
    return app_id


def _process_pipeline(app_id: str):
    """Processes applicant documents if available, then verifies, predicts risk, and scores."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    app_dir = os.path.join(project_root, "data", "applicants", app_id)

    client.post("/api/v1/applications", json={
        "application_id": app_id,
        "applicant_name": f"Synthetic Applicant {app_id}",
        "loan_amount": 1000000.0
    })

    if os.path.exists(app_dir):
        for fname in sorted(os.listdir(app_dir)):
            if not fname.endswith(".txt"):
                continue

            fpath = os.path.join(app_dir, fname)
            with open(fpath, "rb") as f:
                content = f.read()

            upload_res = client.post(
                f"/api/v1/applications/{app_id}/documents",
                files={"file": (fname, content, "text/plain")},
                data={"document_type": "OTHER"}
            )

            if upload_res.status_code == 201:
                doc_id = upload_res.json()["document_id"]
            elif upload_res.status_code == 409:
                docs_res = client.get(f"/api/v1/applications/{app_id}/documents")
                doc_list = docs_res.json().get("documents", [])
                matching = [d for d in doc_list if d["original_filename"] == fname]
                if matching:
                    doc_id = matching[0]["document_id"]
                else:
                    continue
            else:
                pytest.fail(f"Upload failed: {upload_res.text}")

            client.post(f"/api/v1/documents/{doc_id}/extract-text")
            client.post(f"/api/v1/documents/{doc_id}/classify")
            client.post(f"/api/v1/documents/{doc_id}/extract-fields")
            client.post(f"/api/v1/documents/{doc_id}/validate")

    client.post(f"/api/v1/applications/{app_id}/verify")
    client.post(f"/api/v1/applications/{app_id}/risk/predict")
    client.post(f"/api/v1/applications/{app_id}/review-score")


@pytest.fixture(autouse=True)
def clean_human_reviews():
    """Clean human_reviews and human_review_audits tables before and after each test."""
    db = SessionLocal()
    try:
        db.query(HumanReviewAuditModel).delete()
        db.query(HumanReviewModel).delete()
        db.commit()
    finally:
        db.close()
    yield
    db2 = SessionLocal()
    try:
        db2.query(HumanReviewAuditModel).delete()
        db2.query(HumanReviewModel).delete()
        db2.commit()
    finally:
        db2.close()


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── TEST 1: Human decision is stored ──────────────────────────────────────────

def test_human_decision_is_stored(db):
    """TEST 1: Human decision is cleanly persisted on the review record."""
    app_id = "DEC-STORE-01"
    _create_app(app_id)

    res = client.post(
        f"/api/v1/applications/{app_id}/human-review/decision",
        json={
            "officer_id": "OFF-101",
            "decision": "OFFICER_INVESTIGATION",
            "decision_reason": "Follow-up required on employment confirmation.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["human_decision"] == "OFFICER_INVESTIGATION"
    assert data["reviewed_by"] == "OFF-101"


# ── TEST 2: AI recommendation is preserved ───────────────────────────────────

def test_ai_recommendation_is_preserved(db):
    """TEST 2: AI recommendation remains intact after recording human decision."""
    _process_pipeline("A001")
    gate_res = client.get("/api/v1/applications/A001/human-review")
    ai_rec = gate_res.json()["ai_recommendation"]
    assert ai_rec == "STANDARD_REVIEW"

    # Human decides APPROVED
    dec_res = client.post(
        "/api/v1/applications/A001/human-review/decision",
        json={
            "officer_id": "OFF-101",
            "decision": "APPROVED",
            "decision_reason": "All documents verified.",
        },
    )
    assert dec_res.status_code == 200
    assert dec_res.json()["ai_recommendation"] == "STANDARD_REVIEW"


# ── TEST 3: Human decision is preserved separately from AI recommendation ─────

def test_human_decision_preserved_separately(db):
    """TEST 3: AI recommendation and human decision remain strictly in distinct fields."""
    _process_pipeline("A006")
    dec_res = client.post(
        "/api/v1/applications/A006/human-review/decision",
        json={
            "officer_id": "OFF-102",
            "decision": "REJECTED",
            "decision_reason": "Identity mismatch could not be resolved.",
            "override_reason": "Rejecting despite investigation recommendation.",
        },
    )
    assert dec_res.status_code == 200
    data = dec_res.json()
    assert data["ai_recommendation"] == "OFFICER_INVESTIGATION"
    assert data["human_decision"] == "REJECTED"
    assert data["ai_recommendation"] != data["human_decision"]


# ── TEST 4: Aligned decision is detected (ALIGNED) ───────────────────────────

def test_aligned_decision_detected(db):
    """TEST 4: When human decision aligns with AI recommendation, alignment_status is ALIGNED."""
    _process_pipeline("A001")
    # AI recommends STANDARD_REVIEW, officer decides APPROVED
    client.post(
        "/api/v1/applications/A001/human-review/decision",
        json={
            "officer_id": "OFF-103",
            "decision": "APPROVED",
            "decision_reason": "Clean profile, income and KYC verified.",
        },
    )

    hist_res = client.get("/api/v1/applications/A001/decision-history")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["alignment_status"] == "ALIGNED"
    assert hist["human_decision"] == "APPROVED"
    assert hist["ai_recommendation"] == "STANDARD_REVIEW"


# ── TEST 5: Override is detected (OVERRIDDEN) ─────────────────────────────────

def test_override_is_detected(db):
    """TEST 5: When human decision deviates from AI recommendation, alignment_status is OVERRIDDEN."""
    _process_pipeline("A006")
    # AI recommends OFFICER_INVESTIGATION, officer decides APPROVED with manual override reason
    client.post(
        "/api/v1/applications/A006/human-review/decision",
        json={
            "officer_id": "OFF-104",
            "decision": "APPROVED",
            "decision_reason": "Identity verified manually in-branch with gazette notification.",
            "override_reason": "Identity verified manually in-branch with gazette notification.",
        },
    )

    hist_res = client.get("/api/v1/applications/A006/decision-history")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["alignment_status"] == "OVERRIDDEN"
    assert hist["human_decision"] == "APPROVED"
    assert hist["ai_recommendation"] == "OFFICER_INVESTIGATION"
    assert "gazette notification" in hist["decision_reason"]


# ── TEST 6: Existing override reason requirement still works ─────────────────

def test_override_reason_requirement_still_works(db):
    """TEST 6: Deviating decision without override reason fails with 400."""
    _process_pipeline("A006")
    # Attempting to override without any reason:
    bad_res = client.post(
        "/api/v1/applications/A006/human-review/decision",
        json={
            "officer_id": "OFF-105",
            "decision": "APPROVED",
            # No decision_reason, no override_reason
        },
    )
    assert bad_res.status_code == 400
    assert "reason" in bad_res.text.lower()


# ── TEST 7: Decision reason is stored and required for APPROVED/REJECTED ──────

def test_decision_reason_stored_and_required(db):
    """TEST 7: Reason is required for APPROVED and REJECTED, and stored."""
    app_id = "DEC-REASON-REQ"
    _create_app(app_id)

    # Attempt APPROVED with empty reason -> 400
    empty_res = client.post(
        f"/api/v1/applications/{app_id}/human-review/decision",
        json={
            "officer_id": "OFF-106",
            "decision": "APPROVED",
            "decision_reason": "   ",
        },
    )
    assert empty_res.status_code == 400
    assert "reason is required" in empty_res.text.lower()

    # Attempt APPROVED with valid reason -> 200
    ok_res = client.post(
        f"/api/v1/applications/{app_id}/human-review/decision",
        json={
            "officer_id": "OFF-106",
            "decision": "APPROVED",
            "decision_reason": "Salary slips and KYC verified manually.",
        },
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["decision_reason"] == "Salary slips and KYC verified manually."


# ── TEST 8: Officer feedback is stored (text and category) ───────────────────

def test_officer_feedback_stored(db):
    """TEST 8: Submitting feedback saves text and category and logs audit event."""
    app_id = "FB-TEST-01"
    _create_app(app_id)

    fb_res = client.post(
        f"/api/v1/applications/{app_id}/feedback",
        json={
            "officer_id": "OFF-107",
            "feedback": "AI correctly highlighted income discrepancy across documents.",
            "category": "CORRECT",
        },
    )
    assert fb_res.status_code == 200
    fb_data = fb_res.json()
    assert fb_data["officer_id"] == "OFF-107"
    assert fb_data["category"] == "CORRECT"
    assert "income discrepancy" in fb_data["feedback"]
    assert "feedback_id" in fb_data

    # Check that it appears in human-review endpoint
    review_res = client.get(f"/api/v1/applications/{app_id}/human-review")
    feedback_list = review_res.json().get("officer_feedback", [])
    assert len(feedback_list) == 1
    assert feedback_list[0]["category"] == "CORRECT"


# ── TEST 9: Decision history API returns complete history ─────────────────────

def test_decision_history_api_complete(db):
    """TEST 9: GET /decision-history returns full history, alignment, feedback, and audit events."""
    app_id = "DEC-HIST-01"
    _create_app(app_id)

    # 1. Add feedback
    client.post(
        f"/api/v1/applications/{app_id}/feedback",
        json={
            "officer_id": "OFF-108",
            "feedback": "Preliminary check passed.",
            "category": "PARTIALLY_CORRECT",
        },
    )

    # 2. Record decision
    client.post(
        f"/api/v1/applications/{app_id}/human-review/decision",
        json={
            "officer_id": "OFF-108",
            "decision": "APPROVED",
            "decision_reason": "Collateral and income verified.",
        },
    )

    hist_res = client.get(f"/api/v1/applications/{app_id}/decision-history")
    assert hist_res.status_code == 200
    hist = hist_res.json()

    assert hist["application_id"] == app_id
    assert hist["human_decision"] == "APPROVED"
    assert hist["decision_reason"] == "Collateral and income verified."
    assert len(hist["feedback"]) == 1
    assert hist["feedback"][0]["category"] == "PARTIALLY_CORRECT"
    assert len(hist["history"]) >= 2
    actions = [ev["action"] for ev in hist["history"]]
    assert "OFFICER_FEEDBACK_ADDED" in actions
    assert "HUMAN_DECISION_RECORDED" in actions


# ── TEST 10: Cross-applicant isolation works ──────────────────────────────────

def test_cross_applicant_isolation(db):
    """TEST 10: Feedback and decision history for one applicant do not leak to another."""
    app_a = "APP-HIST-ALPHA"
    app_b = "APP-HIST-BETA"
    _create_app(app_a)
    _create_app(app_b)

    # Alpha: decision + feedback
    client.post(
        f"/api/v1/applications/{app_a}/feedback",
        json={"officer_id": "OFF-A", "feedback": "Alpha confidential feedback.", "category": "CORRECT"},
    )
    client.post(
        f"/api/v1/applications/{app_a}/human-review/decision",
        json={"officer_id": "OFF-A", "decision": "APPROVED", "decision_reason": "Alpha approved."},
    )

    # Beta: no decision yet
    beta_hist = client.get(f"/api/v1/applications/{app_b}/decision-history").json()
    assert beta_hist["application_id"] == app_b
    assert beta_hist["human_decision"] is None
    assert beta_hist["alignment_status"] == "PENDING"
    assert len(beta_hist["feedback"]) == 0
    assert "Alpha" not in str(beta_hist)


# ── TEST 11: Invalid application returns 404 ─────────────────────────────────

def test_invalid_application_returns_404(db):
    """TEST 11: Non-existent application returns 404 for feedback and decision-history."""
    res_fb = client.post(
        "/api/v1/applications/NON-EXISTENT-999/feedback",
        json={"officer_id": "OFF-1", "feedback": "Test feedback."},
    )
    assert res_fb.status_code == 404

    res_hist = client.get("/api/v1/applications/NON-EXISTENT-999/decision-history")
    assert res_hist.status_code == 404


# ── TEST 12: Reference Demo Cases (A001, A003, A006) ─────────────────────────

def test_demo_cases_a001_a003_a006(db):
    """TEST 12: Verifies required hackathon demo applications A001, A003, and A006."""
    # A001: Clean case -> ALIGNED approval + feedback
    _process_pipeline("A001")
    client.post(
        "/api/v1/applications/A001/feedback",
        json={"officer_id": "OFFICER-DEMO", "feedback": "AI analysis was completely accurate.", "category": "CORRECT"},
    )
    client.post(
        "/api/v1/applications/A001/human-review/decision",
        json={"officer_id": "OFFICER-DEMO", "decision": "APPROVED", "decision_reason": "All documents verified cleanly."},
    )
    a001_hist = client.get("/api/v1/applications/A001/decision-history").json()
    assert a001_hist["alignment_status"] == "ALIGNED"
    assert a001_hist["human_decision"] == "APPROVED"

    # A006: Identity mismatch -> OVERRIDDEN with reason
    _process_pipeline("A006")
    client.post(
        "/api/v1/applications/A006/human-review/decision",
        json={
            "officer_id": "OFFICER-DEMO",
            "decision": "APPROVED",
            "decision_reason": "Officer manually verified the identity.",
            "override_reason": "Officer manually verified the identity.",
        },
    )
    a006_hist = client.get("/api/v1/applications/A006/decision-history").json()
    assert a006_hist["alignment_status"] == "OVERRIDDEN"
    assert a006_hist["ai_recommendation"] == "OFFICER_INVESTIGATION"
    assert a006_hist["human_decision"] == "APPROVED"
    assert "manually verified" in a006_hist["decision_reason"]

    # A003: Missing tax return -> Request doc + Feedback
    _process_pipeline("A003")
    client.post(
        "/api/v1/applications/A003/human-review/request-documents",
        json={"officer_id": "OFFICER-DEMO", "documents": ["TAX_RETURN"], "reason": "Need latest ITR."},
    )
    client.post(
        "/api/v1/applications/A003/feedback",
        json={"officer_id": "OFFICER-DEMO", "feedback": "Additional document required.", "category": "CORRECT"},
    )
    a003_hist = client.get("/api/v1/applications/A003/decision-history").json()
    assert a003_hist["ai_recommendation"] == "DOCUMENT_FOLLOWUP"
    assert len(a003_hist["feedback"]) == 1
    assert a003_hist["feedback"][0]["feedback"] == "Additional document required."
