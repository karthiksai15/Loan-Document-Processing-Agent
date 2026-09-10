"""
Phase 16 AI Review Agent — A006 Audit & Hardening Test Suite

Verifies requirements A through K:
  A. get_evidence returns actual A006 evidence.
  B. get_verification_findings returns actual A006 findings.
  C. Agent state contains tool results after INSPECT_RESULT.
  D. Final review uses canonical evidence/findings.
  E. Public HDFC policy displays [HDFC_BANK].
  F. Simulated HDFC policy displays [INTERNAL_DEMO].
  G. Identity mismatch does not become confirmed fraud.
  H. A006 recommends OFFICER_INVESTIGATION.
  I. ML risk remains separate from fraud/final decision.
  J. Grounding accepts only valid evidence/policy references.
  K. Optimized Agent remains within expected fake-provider call limits.
"""

import os
import pytest
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import (
    LoanApplicationModel,
    AgentReviewModel,
    EvidenceNodeModel,
    ApplicationVerificationModel,
    VerificationFindingModel,
)
from app.agent import agent_service
from app.agent.tools import (
    get_evidence,
    get_verification_findings,
    get_risk_analysis,
    get_review_score,
    search_policy,
    format_policy_source_label,
)
from app.agent.graph import sanitize_fraud_language
from app.providers.fake_llm_provider import FakeLLMProvider
from app.services.llm_grounding_service import validate_evidence_citations, validate_policy_citations


from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _ensure_a006(db: Session):
    evi_count = db.query(EvidenceNodeModel).filter(EvidenceNodeModel.application_id == "A006").count()
    if evi_count >= 40:
        return

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    app_dir = os.path.join(project_root, "data", "applicants", "A006")

    client.post("/api/v1/applications", json={
        "application_id": "A006",
        "applicant_name": "Synthetic Applicant A006",
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
                "/api/v1/applications/A006/documents",
                files={"file": (fname, content, "text/plain")},
                data={"document_type": "OTHER"}
            )

            if upload_res.status_code == 201:
                doc_id = upload_res.json()["document_id"]
            elif upload_res.status_code == 409:
                docs_res = client.get("/api/v1/applications/A006/documents")
                doc_list = docs_res.json().get("documents", [])
                matching = [d for d in doc_list if d["original_filename"] == fname]
                if matching:
                    doc_id = matching[0]["document_id"]
                else:
                    continue
            else:
                continue

            client.post(f"/api/v1/documents/{doc_id}/extract-text")
            client.post(f"/api/v1/documents/{doc_id}/classify")
            client.post(f"/api/v1/documents/{doc_id}/extract-fields")
            client.post(f"/api/v1/documents/{doc_id}/validate")

    client.post("/api/v1/applications/A006/verify")
    client.post("/api/v1/applications/A006/risk/predict")
    client.post("/api/v1/applications/A006/review-score")
    client.post("/api/v1/applications/A006/evidence")


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def clean_agent_reviews(db):
    _ensure_a006(db)
    db.query(AgentReviewModel).delete()
    db.commit()
    yield
    db.query(AgentReviewModel).delete()
    db.commit()


# ── TEST A: get_evidence returns actual A006 evidence ─────────────────────────

def test_a_get_evidence_returns_actual_a006_evidence(db: Session):
    """TEST A: get_evidence tool returns the actual 50 evidence nodes for A006."""
    res = get_evidence("A006", db)

    assert res["status"] == "OK"
    assert res["application_id"] == "A006"
    assert res["total_nodes"] >= 40  # 50 nodes in seeded database
    assert "node_ids" in res
    assert len(res["node_ids"]) == res["total_nodes"]
    assert "nodes" in res
    assert len(res["nodes"]) == res["total_nodes"]

    # Verify key node types are present
    assert "APPLICATION" in res["node_types"]
    assert "DOCUMENT" in res["node_types"]
    assert "VERIFICATION_FINDING" in res["node_types"]
    assert "ML_RISK_ASSESSMENT" in res["node_types"]
    assert "REVIEW_ASSESSMENT" in res["node_types"]

    # Verify specific nodes exist
    assert "NODE-APP-A006" in res["node_ids"]
    assert "NODE-ML-RISK-A006" in res["node_ids"]
    assert "NODE-REVIEW-A006" in res["node_ids"]


# ── TEST B: get_verification_findings returns actual A006 findings ───────────

def test_b_get_verification_findings_returns_actual_a006_findings(db: Session):
    """TEST B: get_verification_findings tool returns 4 mismatches and finding details for A006."""
    res = get_verification_findings("A006", db)

    assert res["status"] == "OK"
    assert res["application_id"] == "A006"
    assert res["overall_result"] == "MISMATCHES_FOUND"
    assert res["total_comparisons"] == 8
    assert res["mismatched"] == 4
    assert res["mismatched_comparisons"] == 4
    assert len(res["mismatches"]) == 4
    assert len(res["evidence_node_ids"]) == 8

    # Verify primary identity mismatch
    identity_mismatches = [
        m for m in res["mismatches"]
        if m["rule_name"] == "app_name_vs_kyc_name"
    ]
    assert len(identity_mismatches) == 1
    im = identity_mismatches[0]
    assert "Meera Nair" in str(im["value_a"])
    assert "Kiran Mismatch" in str(im["value_b"])


# ── TEST C: Agent state contains tool results after INSPECT_RESULT ───────────

def test_c_agent_state_contains_tool_results_after_inspect_result(db: Session):
    """TEST C: Agent trace and findings accurately reflect tool outputs after INSPECT_RESULT."""
    fake = FakeLLMProvider(
        tool_sequence=["get_evidence", "get_verification_findings"],
        executive_summary="Review of A006 completed.",
        recommended_next_step="OFFICER_INVESTIGATION",
    )
    res = agent_service.run_agent_review(db, "A006", force_rebuild=True, provider_override=fake)

    steps = res["investigation_steps"]
    inspect_steps = [s for s in steps if s["action"] == "INSPECT_RESULT"]
    assert len(inspect_steps) >= 2

    # Verify get_evidence inspect step reports real node count (>0, not 0)
    ev_inspect = [s for s in inspect_steps if s.get("tool_name") == "get_evidence"]
    assert len(ev_inspect) == 1
    assert "(0 node(s))" not in ev_inspect[0]["result_summary"]
    assert "node(s)" in ev_inspect[0]["result_summary"]
    assert "50 node(s)" in ev_inspect[0]["result_summary"]

    # Verify get_verification_findings inspect step reports 4 mismatches (not 0)
    vf_inspect = [s for s in inspect_steps if s.get("tool_name") == "get_verification_findings"]
    assert len(vf_inspect) == 1
    assert "4 mismatch(es)" in vf_inspect[0]["result_summary"]
    assert "0 mismatch(es)" not in vf_inspect[0]["result_summary"]


# ── TEST D: Final review uses canonical evidence/findings ───────────────────

def test_d_final_review_uses_canonical_evidence_and_findings(db: Session):
    """TEST D: Final review contains grounded evidence citations from the graph."""
    fake = FakeLLMProvider(
        tool_sequence=["get_evidence"],
        recommended_next_step="OFFICER_INVESTIGATION",
    )
    res = agent_service.run_agent_review(db, "A006", force_rebuild=True, provider_override=fake)

    final_rev = res["final_review"]
    evidence_refs = final_rev.get("evidence_references", [])
    assert len(evidence_refs) > 0

    # Ensure cited IDs exist in the DB for A006
    valid_ids, invalid_ids = validate_evidence_citations(
        "A006",
        [r["node_id"] for r in evidence_refs],
        db
    )
    assert len(invalid_ids) == 0
    assert len(valid_ids) == len(evidence_refs)


# ── TEST E: Public HDFC policy displays [HDFC_BANK] ─────────────────────────

def test_e_public_hdfc_policy_displays_hdfc_bank(db: Session):
    """TEST E: Public HDFC Bank policies display HDFC_BANK, never INTERNAL_BANK."""
    label = format_policy_source_label("HDFC_BANK", False, "POL_HDFC_PUB_CREDITWORTHINESS_003")
    assert label == "HDFC_BANK"

    # Search policy check
    res = search_policy("credit score CIBIL threshold", db)
    hdfc_pub = [p for p in res.get("results", []) if "HDFC_PUB" in p["policy_id"]]
    if hdfc_pub:
        assert hdfc_pub[0]["source_label"] == "HDFC_BANK"
        assert hdfc_pub[0]["source_label"] != "INTERNAL_BANK"


# ── TEST F: Simulated HDFC policy displays [INTERNAL_DEMO] ───────────────────

def test_f_simulated_hdfc_policy_displays_internal_demo(db: Session):
    """TEST F: Simulated demo policies display INTERNAL_DEMO."""
    label = format_policy_source_label("HDFC_INTERNAL_DEMO", True, "POL_HDFC_DEMO_IDENTITY_MISMATCH_003")
    assert label == "INTERNAL_DEMO"

    # Search policy check
    res = search_policy("critical identity mismatch", db)
    demo_pols = [p for p in res.get("results", []) if "DEMO" in p["policy_id"]]
    if demo_pols:
        assert demo_pols[0]["source_label"] == "INTERNAL_DEMO"
        assert demo_pols[0]["is_simulated"] is True


# ── TEST G: Identity mismatch does not become confirmed fraud ─────────────────

def test_g_identity_mismatch_does_not_become_confirmed_fraud(db: Session):
    """TEST G: Overly strong fraud assertions are sanitized to safe factual wording."""
    raw_summary = "Application A006 mandatory officer investigation is required to rule out potential identity fraud."
    sanitized = sanitize_fraud_language(raw_summary)

    assert "potential identity fraud" not in sanitized.lower()
    assert "A primary identity mismatch requires officer investigation before further automated processing." in sanitized

    # Test full review flow with simulated fraud language
    fake = FakeLLMProvider(
        executive_summary="Review of A006: mandatory officer investigation is required to rule out potential identity fraud.",
        key_findings=[
            "Application exhibits potential identity fraud between PAN and Aadhaar.",
            "Identity fraud investigation is mandatory."
        ],
        recommended_next_step="OFFICER_INVESTIGATION",
    )
    res = agent_service.run_agent_review(db, "A006", force_rebuild=True, provider_override=fake)

    final_rev = res["final_review"]
    summary = final_rev["executive_summary"]
    assert "potential identity fraud" not in summary.lower()
    for finding in final_rev["key_findings"]:
        assert "potential identity fraud" not in finding.lower()


# ── TEST H: A006 recommends OFFICER_INVESTIGATION ───────────────────────────

def test_h_a006_recommends_officer_investigation(db: Session):
    """TEST H: A006 with identity mismatch recommends OFFICER_INVESTIGATION or ESCALATE."""
    fake = FakeLLMProvider(
        recommended_next_step="OFFICER_INVESTIGATION",
    )
    res = agent_service.run_agent_review(db, "A006", force_rebuild=True, provider_override=fake)

    action = res["final_review"]["recommended_next_step"]
    assert action in ("OFFICER_INVESTIGATION", "ESCALATE")
    assert action not in ("APPROVED", "REJECTED")


# ── TEST I: ML risk remains separate from fraud/final decision ───────────────

def test_i_ml_risk_remains_separate_from_fraud_final_decision(db: Session):
    """TEST I: ML output is framed as a historical rejection-risk indicator, not a decision/fraud score."""
    ra = get_risk_analysis("A006", db)

    assert ra["status"] == "OK"
    assert ra["risk_level"] == "LOW"
    assert abs(ra["rejection_probability"] - 0.0566) < 0.01  # approximately 5.66%
    assert ra["ml_probability"] == ra["rejection_probability"]
    assert ra["ml_risk_level"] == "LOW"

    note = ra["interpretation_note"].lower()
    assert "historical rejection risk indicator" in note
    assert "not a guaranteed default probability" in note
    assert "not a fraud model" in note
    assert "not an automatic credit decision" in note


# ── TEST J: Grounding accepts only valid evidence/policy references ──────────

def test_j_grounding_accepts_only_valid_evidence_policy_references(db: Session):
    """TEST J: Grounding validator accepts real IDs and detects fabricated ones."""
    # Test evidence grounding
    valid_ev, invalid_ev = validate_evidence_citations(
        "A006",
        ["NODE-APP-A006", "NODE-FABRICATED-EVIDENCE-XYZ"],
        db
    )
    assert valid_ev == ["NODE-APP-A006"]
    assert invalid_ev == ["NODE-FABRICATED-EVIDENCE-XYZ"]

    # Test policy grounding
    valid_pol, invalid_pol = validate_policy_citations(
        ["POL_HDFC_DEMO_IDENTITY_MISMATCH_003", "POL_FABRICATED_POLICY_XYZ"],
        db
    )
    assert valid_pol == ["POL_HDFC_DEMO_IDENTITY_MISMATCH_003"]
    assert invalid_pol == ["POL_FABRICATED_POLICY_XYZ"]


# ── TEST K: Optimized Agent remains within expected fake-provider call limits ─

def test_k_optimized_agent_within_call_limits(db: Session):
    """TEST K: Agent uses batch planning and executes in 1 to 3 LLM calls."""
    fake = FakeLLMProvider(
        planned_tools=["get_evidence", "get_verification_findings", "search_policy"],
        recommended_next_step="OFFICER_INVESTIGATION",
    )
    res = agent_service.run_agent_review(db, "A006", force_rebuild=True, provider_override=fake)

    # In our optimized flow:
    # Call 1: ANALYZE_CASE (plans tools)
    # Intermediate tools execute deterministically via planned queue without LLM roundtrips
    # Call 2: BUILD_REVIEW (synthesizes findings)
    assert fake.call_count in (1, 2, 3)
    assert res["investigation_status"] in ("COMPLETED", "ESCALATED")
