"""
Phase 18 — Confidence + Human-in-the-Loop Review Tests

Tests cover all 24 required verification points:
  1. Confidence evaluation on clean application (A001: score >= 80, HIGH level)
  2. Explainable factor breakdown (7 factors, weights sum to 100%)
  3. Identity mismatch penalty & cap (A006: score <= 45, LOW level)
  4. Missing documents penalty & cap (score <= 35, LOW level)
  5. Degraded investigation penalty & cap (score <= 25, LOW level)
  6. Gate trigger for identity mismatch (A006 -> REQUIRED, IDENTITY_MISMATCH ERROR)
  7. Clean application fast-path (A001 -> NOT_REQUIRED, empty reasons)
  8. Gate trigger for missing mandatory tax return (A003 -> REQUIRED)
  9. Gate trigger for missing mandatory bank statement (A009 -> REQUIRED)
  10. Gate trigger for high ML risk priority (A007 -> REQUIRED, HIGH_RISK_PRIORITY)
  11. Gate trigger for low confidence score
  12. Gate trigger for AI safety escalation
  13. Structured human review reasons schema (code, severity, description)
  14. Officer workflow: acknowledge review (REQUIRED -> IN_REVIEW)
  15. Officer workflow: add officer notes
  16. Officer workflow: request additional documents
  17. Human decision workflow: aligned decision (COMPLETED, override=False)
  18. Human decision workflow: override requires mandatory override_reason
  19. Human decision workflow: override success (OVERRIDDEN, override=True)
  20. Strict separation: AI never approves or rejects loans
  21. Audit trail: complete chronological actions recorded
  22. Audit trail privacy: no raw PII or secret LLM chain-of-thought
  23. Cross-applicant data isolation
  24. Error handling: 404 for missing applications, 400 for invalid inputs
"""

import os
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import (
    HumanReviewModel,
    HumanReviewAuditModel,
    AgentReviewModel,
    LoanApplicationModel,
)
from app.db.session import SessionLocal
from app.services.confidence_service import evaluate_confidence
from app.services import human_review_service

client = TestClient(app)

ALLOWED_HUMAN_DECISIONS = {
    "APPROVED",
    "REJECTED",
    "OFFICER_INVESTIGATION",
    "DOCUMENT_FOLLOWUP",
    "ESCALATED",
}
FORBIDDEN_AI_RECOMMENDATIONS = {"APPROVED", "REJECTED", "APPROVE", "REJECT"}


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


# ── TEST 1: Clean Application High Confidence (A001) ─────────────────────────

def test_confidence_evaluation_clean_high_confidence(db):
    """TEST 1: Normal clean application A001 yields score >= 80 and HIGH confidence level."""
    _process_pipeline("A001")
    conf = evaluate_confidence("A001", db)
    assert conf.score >= 80.0, f"Expected A001 score >= 80, got {conf.score}"
    assert conf.level == "HIGH"
    assert len(conf.penalties_applied) == 0


# ── TEST 2: Factor Breakdown Explainability ───────────────────────────────────

def test_confidence_factor_breakdown_explainability(db):
    """TEST 2: Breakdown includes 7 explainable factors with weights summing to 100%."""
    _create_app("CONF-BREAKDOWN-APP")
    conf = evaluate_confidence("CONF-BREAKDOWN-APP", db)

    factor_names = {f.name for f in conf.breakdown}
    expected_factors = {
        "evidence_sufficiency",
        "evidence_trust",
        "document_completeness",
        "verification_consistency",
        "policy_grounding",
        "claim_grounding",
        "investigation_status",
    }
    assert expected_factors == factor_names

    total_weight = sum(f.weight for f in conf.breakdown)
    assert abs(total_weight - 100.0) < 1e-3

    for f in conf.breakdown:
        assert 0.0 <= f.score <= 100.0
        assert 0.0 <= f.weighted_score <= 100.0
        assert len(f.explanation) > 0


# ── TEST 3: Identity Mismatch Penalty & Cap (A006) ───────────────────────────

def test_confidence_identity_mismatch_penalty_and_cap(db):
    """TEST 3: Identity mismatch on A006 caps confidence at 45 (LOW level)."""
    _process_pipeline("A006")
    conf = evaluate_confidence("A006", db)
    assert conf.score <= 45.0, f"Expected A006 score <= 45.0, got {conf.score}"
    assert conf.level == "LOW"
    assert any("identity mismatch" in p.lower() for p in conf.penalties_applied)


# ── TEST 4: Missing Documents Penalty & Cap ───────────────────────────────────

def test_confidence_missing_documents_penalty_and_cap(db):
    """TEST 4: Missing >= 2 mandatory documents caps confidence at 35 (LOW level)."""
    app_id = "APP-MISSING-DOCS"
    _create_app(app_id)
    conf = evaluate_confidence(app_id, db)
    assert conf.score <= 35.0, f"Expected missing docs cap <= 35.0, got {conf.score}"
    assert conf.level == "LOW"
    assert any("mandatory documents missing" in p.lower() for p in conf.penalties_applied)


# ── TEST 5: Degraded Investigation Penalty & Cap ─────────────────────────────

def test_confidence_degraded_investigation_cap(db):
    """TEST 5: Degraded investigation caps confidence at 25 (LOW level)."""
    app_id = "APP-DEGRADED-INV"
    _create_app(app_id)

    # Insert a degraded agent review
    rev = AgentReviewModel(
        agent_review_id=f"REV-DEG-{uuid.uuid4().hex[:6]}",
        application_id=app_id,
        investigation_status="DEGRADED",
        step_count=2,
        executive_summary="Investigation degraded.",
        recommended_next_step="OFFICER_INVESTIGATION",
        confidence=0.2,
        confidence_level="LOW",
    )
    db.add(rev)
    db.commit()

    conf = evaluate_confidence(app_id, db, agent_review=rev)
    assert conf.score <= 25.0, f"Expected degraded cap <= 25.0, got {conf.score}"
    assert conf.level == "LOW"
    assert any("degraded" in p.lower() for p in conf.penalties_applied)


# ── TEST 6: Gate Trigger for Identity Mismatch (A006) ─────────────────────────

def test_gate_trigger_identity_mismatch_a006(db):
    """TEST 6: A006 identity mismatch triggers REQUIRED review with IDENTITY_MISMATCH reason."""
    _process_pipeline("A006")
    res = client.post("/api/v1/applications/A006/human-review")
    assert res.status_code == 200
    data = res.json()

    assert data["human_review_required"] is True
    assert data["human_review_status"] == "REQUIRED"
    assert data["confidence_level"] == "LOW"
    assert data["confidence_score"] <= 45.0

    reason_codes = [r["code"] for r in data["reasons"]]
    assert "IDENTITY_MISMATCH" in reason_codes
    identity_reason = next(r for r in data["reasons"] if r["code"] == "IDENTITY_MISMATCH")
    assert identity_reason["severity"] == "ERROR"


# ── TEST 7: Clean Application Fast-Path (A001) ───────────────────────────────

def test_gate_clean_application_a001(db):
    """TEST 7: Clean application A001 produces NOT_REQUIRED review."""
    _process_pipeline("A001")
    res = client.post("/api/v1/applications/A001/human-review")
    assert res.status_code == 200
    data = res.json()

    assert data["human_review_required"] is False
    assert data["human_review_status"] == "NOT_REQUIRED"
    assert data["confidence_level"] == "HIGH"
    assert len(data["reasons"]) == 0


# ── TEST 8: Gate Trigger for Missing Tax Return (A003) ────────────────────────

def test_gate_trigger_missing_mandatory_documents_a003(db):
    """TEST 8: A003 (missing tax return) triggers REQUIRED review."""
    _process_pipeline("A003")
    res = client.post("/api/v1/applications/A003/human-review")
    assert res.status_code == 200
    data = res.json()

    assert data["human_review_required"] is True
    assert data["human_review_status"] == "REQUIRED"
    reason_codes = [r["code"] for r in data["reasons"]]
    assert "MISSING_MANDATORY_DOCUMENTS" in reason_codes


# ── TEST 9: Gate Trigger for Missing Bank Statement (A009) ───────────────────

def test_gate_trigger_missing_mandatory_documents_a009(db):
    """TEST 9: A009 (missing bank statement) triggers REQUIRED review."""
    _process_pipeline("A009")
    res = client.post("/api/v1/applications/A009/human-review")
    assert res.status_code == 200
    data = res.json()

    assert data["human_review_required"] is True
    assert data["human_review_status"] == "REQUIRED"
    reason_codes = [r["code"] for r in data["reasons"]]
    assert "MISSING_MANDATORY_DOCUMENTS" in reason_codes


# ── TEST 10: Gate Trigger for High ML Risk (A007) ─────────────────────────────

def test_gate_trigger_high_ml_risk_a007(db):
    """TEST 10: A007 with high historical risk triggers REQUIRED review with HIGH_RISK_PRIORITY."""
    _process_pipeline("A007")
    res = client.post("/api/v1/applications/A007/human-review")
    assert res.status_code == 200
    data = res.json()

    assert data["human_review_required"] is True
    assert data["human_review_status"] == "REQUIRED"
    reason_codes = [r["code"] for r in data["reasons"]]
    assert "HIGH_RISK_PRIORITY" in reason_codes


# ── TEST 11: Gate Trigger for Low Confidence Score ────────────────────────────

def test_gate_trigger_low_confidence(db):
    """TEST 11: Application with low confidence triggers LOW_CONFIDENCE reason."""
    app_id = "APP-LOW-CONF"
    _create_app(app_id)
    res = client.post(f"/api/v1/applications/{app_id}/human-review")
    assert res.status_code == 200
    data = res.json()

    assert data["human_review_required"] is True
    reason_codes = [r["code"] for r in data["reasons"]]
    assert "LOW_CONFIDENCE" in reason_codes


# ── TEST 12: Gate Trigger for AI Safety Escalation ───────────────────────────

def test_gate_trigger_safety_escalation(db):
    """TEST 12: Application where agent triggered safety escalation triggers SAFETY_ESCALATION reason."""
    app_id = "APP-SAFETY-ESC"
    _create_app(app_id)

    rev = AgentReviewModel(
        agent_review_id=f"REV-ESC-{uuid.uuid4().hex[:6]}",
        application_id=app_id,
        investigation_status="ESCALATED",
        step_count=2,
        executive_summary="Escalated due to suspicious pattern.",
        recommended_next_step="ESCALATE",
        escalation_required=1,
        escalation_reason="Suspicious document layout anomaly.",
        confidence=0.4,
        confidence_level="LOW",
    )
    db.add(rev)
    db.commit()

    res = client.post(f"/api/v1/applications/{app_id}/human-review")
    assert res.status_code == 200
    data = res.json()

    assert data["human_review_required"] is True
    reason_codes = [r["code"] for r in data["reasons"]]
    assert "SAFETY_ESCALATION" in reason_codes
    esc_reason = next(r for r in data["reasons"] if r["code"] == "SAFETY_ESCALATION")
    assert esc_reason["severity"] == "ERROR"


# ── TEST 13: Structured Human Review Reasons ──────────────────────────────────

def test_human_review_reasons_structure(db):
    """TEST 13: Reasons strictly conform to code, severity (ERROR/WARNING), and description."""
    _process_pipeline("A006")
    res = client.get("/api/v1/applications/A006/human-review")
    assert res.status_code == 200
    data = res.json()

    for reason in data["reasons"]:
        assert "code" in reason and len(reason["code"]) > 0
        assert reason["severity"] in ("ERROR", "WARNING")
        assert "description" in reason and len(reason["description"]) > 0


# ── TEST 14: Acknowledge Review Workflow ──────────────────────────────────────

def test_acknowledge_review_workflow(db):
    """TEST 14: Officer acknowledging review transitions REQUIRED -> IN_REVIEW."""
    _process_pipeline("A006")
    # First get gate
    res1 = client.get("/api/v1/applications/A006/human-review")
    assert res1.json()["human_review_status"] == "REQUIRED"

    # Acknowledge
    ack_res = client.post(
        "/api/v1/applications/A006/human-review/acknowledge",
        json={"officer_id": "LOAN-OFFICER-42"},
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["human_review_status"] == "IN_REVIEW"
    assert ack_res.json()["reviewed_by"] == "LOAN-OFFICER-42"


# ── TEST 15: Add Officer Note ────────────────────────────────────────────────

def test_add_officer_note(db):
    """TEST 15: Loan officer can add timestamped notes to the review."""
    _process_pipeline("A006")
    note_res = client.post(
        "/api/v1/applications/A006/human-review/note",
        json={
            "officer_id": "OFFICER-JOHN",
            "note": "Contacted applicant to request clarification on name mismatch.",
        },
    )
    assert note_res.status_code == 200
    notes = note_res.json()["officer_notes"]
    assert len(notes) == 1
    assert notes[0]["officer_id"] == "OFFICER-JOHN"
    assert "clarification" in notes[0]["text"]
    assert "timestamp" in notes[0]


# ── TEST 16: Request Additional Documents ─────────────────────────────────────

def test_request_additional_documents(db):
    """TEST 16: Officer requesting documents updates requested_documents and status."""
    _process_pipeline("A003")
    req_res = client.post(
        "/api/v1/applications/A003/human-review/request-documents",
        json={
            "officer_id": "OFFICER-SARAH",
            "documents": ["TAX_RETURN", "FORM_16"],
            "reason": "Need latest 2 years ITR for self-employed income verification.",
        },
    )
    assert req_res.status_code == 200
    data = req_res.json()
    assert data["human_review_status"] == "IN_REVIEW"
    docs = data["requested_documents"]
    assert len(docs) == 2
    types = {d["doc_type"] for d in docs}
    assert "TAX_RETURN" in types
    assert "FORM_16" in types


# ── TEST 17: Record Human Decision Aligned ────────────────────────────────────

def test_record_human_decision_aligned(db):
    """TEST 17: Aligned decision (e.g. OFFICER_INVESTIGATION) completes with override=False."""
    _process_pipeline("A006")
    dec_res = client.post(
        "/api/v1/applications/A006/human-review/decision",
        json={
            "officer_id": "OFFICER-ALEX",
            "decision": "OFFICER_INVESTIGATION",
            "notes": "Agree with AI recommendation to perform field verification.",
        },
    )
    assert dec_res.status_code == 200
    data = dec_res.json()
    assert data["human_decision"] == "OFFICER_INVESTIGATION"
    assert data["override"] is False
    assert data["human_review_status"] == "COMPLETED"


# ── TEST 18: Record Human Decision Override Requires Reason ──────────────────

def test_record_human_decision_override_requires_reason(db):
    """TEST 18: Attempting to override without override_reason fails with 400 Bad Request."""
    _process_pipeline("A006")
    # AI recommendation for A006 is OFFICER_INVESTIGATION. Trying to APPROVED without override_reason:
    dec_res = client.post(
        "/api/v1/applications/A006/human-review/decision",
        json={
            "officer_id": "OFFICER-ALEX",
            "decision": "APPROVED",
            "override_reason": "",  # Empty!
        },
    )
    assert dec_res.status_code == 400
    assert "override reason is mandatory" in dec_res.text.lower()


# ── TEST 19: Record Human Decision Override Success ──────────────────────────

def test_record_human_decision_override_success(db):
    """TEST 19: Providing override_reason records decision with override=True and status=OVERRIDDEN."""
    _process_pipeline("A006")
    dec_res = client.post(
        "/api/v1/applications/A006/human-review/decision",
        json={
            "officer_id": "SENIOR-OFFICER-SMITH",
            "decision": "APPROVED",
            "override_reason": "In-person branch verification verified genuine gazetted name change.",
            "notes": "Affidavit copy collected and archived in branch dossier.",
        },
    )
    assert dec_res.status_code == 200
    data = dec_res.json()
    assert data["human_decision"] == "APPROVED"
    assert data["override"] is True
    assert "gazetted name change" in data["override_reason"]
    assert data["human_review_status"] == "OVERRIDDEN"


# ── TEST 20: AI Never Approves or Rejects Loans ──────────────────────────────

def test_ai_never_approves_or_rejects(db):
    """TEST 20: AI recommendation is strictly separated from human decision and never APPROVES/REJECTS."""
    for demo_app in ["A001", "A003", "A006", "A007", "A009"]:
        _process_pipeline(demo_app)
        res = client.get(f"/api/v1/applications/{demo_app}/human-review")
        assert res.status_code == 200
        ai_rec = res.json()["ai_recommendation"]
        assert ai_rec not in FORBIDDEN_AI_RECOMMENDATIONS, (
            f"AI illegally recommended '{ai_rec}' for application {demo_app}"
        )


# ── TEST 21: Audit Trail Chronology and Actions ──────────────────────────────

def test_audit_trail_chronology_and_actions(db):
    """TEST 21: Complete audit trail records all chronological actions."""
    app_id = "A006"
    _process_pipeline(app_id)

    # 1. Gate Evaluated
    client.post(f"/api/v1/applications/{app_id}/human-review")
    # 2. Acknowledged
    client.post(f"/api/v1/applications/{app_id}/human-review/acknowledge", json={"officer_id": "OFF-1"})
    # 3. Note added
    client.post(f"/api/v1/applications/{app_id}/human-review/note", json={"officer_id": "OFF-1", "note": "Reviewing."})
    # 4. Docs requested
    client.post(f"/api/v1/applications/{app_id}/human-review/request-documents", json={
        "officer_id": "OFF-1",
        "documents": ["AFFIDAVIT"],
        "reason": "Name change proof",
    })
    # 5. Overridden decision
    client.post(f"/api/v1/applications/{app_id}/human-review/decision", json={
        "officer_id": "OFF-1",
        "decision": "APPROVED",
        "override_reason": "Verified affidavit personally.",
    })

    audit_res = client.get(f"/api/v1/applications/{app_id}/human-review/audit")
    assert audit_res.status_code == 200
    data = audit_res.json()

    assert data["total_events"] >= 5
    actions = [ev["action"] for ev in data["events"]]
    assert "HUMAN_REVIEW_GATE_EVALUATED" in actions
    assert "HUMAN_REVIEW_ACKNOWLEDGED" in actions
    assert "OFFICER_NOTE_ADDED" in actions
    assert "DOCUMENTS_REQUESTED" in actions
    assert "AI_RECOMMENDATION_OVERRIDDEN" in actions
    assert "HUMAN_DECISION_RECORDED" in actions


# ── TEST 22: Audit Trail Privacy (No Raw PII or Thoughts) ─────────────────────

def test_audit_trail_privacy_no_raw_pii_or_thoughts(db):
    """TEST 22: Audit trail contains no raw PII or secret LLM chain-of-thought."""
    app_id = "A006"
    _process_pipeline(app_id)
    client.post(f"/api/v1/applications/{app_id}/human-review")

    audit_res = client.get(f"/api/v1/applications/{app_id}/human-review/audit")
    assert audit_res.status_code == 200
    data = audit_res.json()

    for event in data["events"]:
        event_str = str(event).lower()
        assert "aadhaar" not in event_str
        assert "chain_of_thought" not in event_str
        assert "raw_llm_output" not in event_str
        assert event["actor_type"] in ("SYSTEM", "LOAN_OFFICER")


# ── TEST 23: Cross-Applicant Data Isolation ──────────────────────────────────

def test_cross_applicant_isolation(db):
    """TEST 23: Action and audit records for one applicant cannot leak to another."""
    app_1 = "APP-ISO-ALPHA"
    app_2 = "APP-ISO-BETA"
    _create_app(app_1)
    _create_app(app_2)

    client.post(f"/api/v1/applications/{app_1}/human-review")
    client.post(f"/api/v1/applications/{app_1}/human-review/note", json={
        "officer_id": "OFFICER-SECRET",
        "note": "Private note only for Alpha",
    })

    client.post(f"/api/v1/applications/{app_2}/human-review")

    # Inspect Beta
    beta_res = client.get(f"/api/v1/applications/{app_2}/human-review")
    beta_notes = beta_res.json()["officer_notes"]
    assert len(beta_notes) == 0

    beta_audit = client.get(f"/api/v1/applications/{app_2}/human-review/audit")
    for event in beta_audit.json()["events"]:
        assert event["application_id"] == app_2
        assert "Alpha" not in str(event)


# ── TEST 24: Error Handling & Validations ────────────────────────────────────

def test_human_review_invalid_inputs_and_404(db):
    """TEST 24: Validates proper 404 for non-existent apps and 400 for bad input."""
    # 404 on non-existent app
    res_404 = client.get("/api/v1/applications/NON-EXISTENT-XYZ/human-review")
    assert res_404.status_code == 404

    res_audit_404 = client.get("/api/v1/applications/NON-EXISTENT-XYZ/human-review/audit")
    assert res_audit_404.status_code == 404

    # 400 on invalid decision
    _create_app("APP-ERR-TEST")
    bad_dec = client.post(
        "/api/v1/applications/APP-ERR-TEST/human-review/decision",
        json={"officer_id": "OFF-1", "decision": "RANDOM_INVALID_DECISION"},
    )
    assert bad_dec.status_code == 400

    # 400 on empty note
    bad_note = client.post(
        "/api/v1/applications/APP-ERR-TEST/human-review/note",
        json={"officer_id": "OFF-1", "note": ""},
    )
    assert bad_note.status_code == 422 or bad_note.status_code == 400
