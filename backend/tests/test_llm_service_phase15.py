"""
Phase 15 — LLM Service Unit & Integration Tests

Covers all 12 Phase 15 requirements:
  1. LLM service configuration
  2. Missing API key handling (graceful 503, no fake response)
  3. Successful LLM call using mocked provider
  4. Invalid / malformed LLM response handling (fallback)
  5. Structured output validation against Pydantic schema
  6. Policy source separation (RBI vs HDFC_BANK vs HDFC_INTERNAL_DEMO)
  7. Simulated policy labeling ("Simulated HDFC internal/demo rule")
  8. ML risk interpretation (historical rejection-risk indicator, no "reject" decision)
  9. Missing document handling (missing != mismatch)
  10. Conflicting evidence handling (factual conflict, no arbitrary decision)
  11. Concise response behavior
  12. Final-decision safety rule (no APPROVED/REJECTED decision)

Zero external calls to live Groq API.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.providers.gemini_provider import GeminiProvider, GeminiProviderUnavailableException
from app.providers.groq_provider import GroqProvider, GroqProviderUnavailableException
from app.providers.fake_llm_provider import FakeLLMProvider
from app.schemas.llm import (
    LLMDirectReviewRequest,
    LLMReviewResult,
    LLMReviewResponse,
    KeyFinding,
    DocumentPresence,
    RiskAssessment,
    PolicyBasis,
)
from app.services import llm_service
from app.services.llm_prompts import LOAN_REVIEW_SYSTEM_PROMPT, format_direct_review_prompt

client = TestClient(app)


# ── Test 1: LLM service configuration ────────────────────────────────────────

def test_llm_service_configuration():
    """Verify GeminiProvider and GroqProvider instantiation and configuration defaults."""
    # 1. GeminiProvider (Primary default provider)
    gemini_p = GeminiProvider(api_key="test-key-123", model="gemini-2.5-flash")
    assert gemini_p.name() == "GeminiProvider(gemini-2.5-flash)"
    assert gemini_p.is_available() is True
    assert gemini_p.timeout == 60.0

    # Default provider factory returns GeminiProvider
    active_p = llm_service.get_llm_provider_for_review()
    assert isinstance(active_p, GeminiProvider)

    # 2. GroqProvider (Alternative provider)
    groq_p = GroqProvider(api_key="test-key-123", model="openai/gpt-oss-20b", base_url="https://api.groq.com/openai/v1")
    assert groq_p.name() == "GroqProvider(openai/gpt-oss-20b)"
    assert groq_p.is_available() is True
    assert groq_p.base_url == "https://api.groq.com/openai/v1"
    assert groq_p.timeout == 60.0


# ── Test 2: Missing API key handling ─────────────────────────────────────────

def test_missing_api_key_handling():
    """
    When API key is empty / missing:
    - Provider is_available() is False
    - generate() raises ProviderUnavailableException
    - Direct review raises ProviderUnavailableException
    - API endpoint returns HTTP 503 Service Unavailable with clear message
    - Does NOT return a fake LLM response
    """
    # 1. GeminiProvider missing key
    unconfigured_gemini = GeminiProvider(api_key="")
    assert unconfigured_gemini.is_available() is False
    with pytest.raises(GeminiProviderUnavailableException) as exc_gemini:
        unconfigured_gemini.generate("test prompt")
    assert "GEMINI_API_KEY is not configured" in str(exc_gemini.value)

    # 2. GroqProvider missing key
    unconfigured_groq = GroqProvider(api_key="")
    assert unconfigured_groq.is_available() is False
    with pytest.raises(GroqProviderUnavailableException) as exc_groq:
        unconfigured_groq.generate("test prompt")
    assert "GROQ_API_KEY is not configured" in str(exc_groq.value)

    # 3. API endpoint test when active provider (Gemini) is unconfigured
    original_gemini_key = settings.GEMINI_API_KEY
    try:
        settings.GEMINI_API_KEY = ""
        res = client.post("/api/v1/llm/review", json={
            "application_id": "APP-TEST-UNAVAIL",
            "applicant_name": "Test User",
        })
        assert res.status_code == 503
        data = res.json()
        assert "unavailable" in data["detail"].lower()
        # Verify it did not return a fake review
        assert "summary" not in data
    finally:
        settings.GEMINI_API_KEY = original_gemini_key


# ── Test 3: Successful LLM call using mocked provider ───────────────────────

def test_successful_llm_call_mocked_provider():
    """Verify end-to-end direct review execution using a mocked provider."""
    mock_review = {
        "summary": "Application documents verified. Standard salaried applicant with stable profile.",
        "application_status": "COMPLETE",
        "documents": {
            "present": ["PAYSLIP", "BANK_STATEMENT", "KYC"],
            "missing": []
        },
        "key_findings": [
            {
                "issue": "Income verified against bank statement credits",
                "severity": "INFO",
                "evidence": ["Payslip net salary: INR 75,000", "Bank credits: INR 75,000"]
            }
        ],
        "risk_assessment": {
            "ml_probability": 0.12,
            "ml_level": "LOW",
            "evidence_quality": 95.0,
            "review_priority_score": 20.0,
            "review_priority_level": "LOW"
        },
        "policy_basis": [
            {
                "source": "HDFC_BANK",
                "is_simulated": False,
                "policy_name": "HDFC Bank Personal Loan — Public Documentation Checklist for Salaried Applicants",
                "relevance": "Standard retail documentation checklist satisfied."
            }
        ],
        "missing_information": [],
        "investigation_points": [],
        "recommended_next_action": "STANDARD_REVIEW",
        "confidence": 0.90
    }

    mock_provider = FakeLLMProvider(custom_response=json.dumps(mock_review))
    req = LLMDirectReviewRequest(
        application_id="APP-A001-TEST",
        applicant_name="Rohan Sharma",
        loan_amount=500000.0,
        documents_present=["PAYSLIP", "BANK_STATEMENT", "KYC"],
    )

    resp = llm_service.generate_direct_review(request=req, provider_override=mock_provider)

    assert isinstance(resp, LLMReviewResponse)
    assert resp.summary == mock_review["summary"]
    assert resp.application_status == "COMPLETE"
    assert resp.documents["present"] == ["PAYSLIP", "BANK_STATEMENT", "KYC"]
    assert len(resp.key_findings) == 1
    assert resp.key_findings[0]["issue"] == "Income verified against bank statement credits"
    assert resp.recommended_next_action == "STANDARD_REVIEW"
    assert resp.confidence == 0.90
    assert resp.grounding_status == "GROUNDED"


# ── Test 4: Invalid / malformed LLM response handling ────────────────────────

def test_invalid_malformed_llm_response_handling():
    """When LLM returns non-JSON or malformed output, service returns safe fallback review."""
    malformed_provider = FakeLLMProvider(custom_response="Sorry, I cannot process this request into JSON.")
    req = LLMDirectReviewRequest(application_id="APP-MALFORMED-001")

    resp = llm_service.generate_direct_review(request=req, provider_override=malformed_provider)

    assert isinstance(resp, LLMReviewResponse)
    assert resp.confidence == 0.0
    assert "could not be generated" in resp.summary.lower() or "failed" in resp.summary.lower()
    assert resp.recommended_next_action == "OFFICER_INVESTIGATION"
    assert resp.grounding_status == "UNGROUNDED"


# ── Test 5: Structured output validation against Pydantic schema ─────────────

def test_structured_output_validation():
    """Verify that parsed JSON is strictly validated against LLMReviewResult schema."""
    valid_data = {
        "summary": "Concise review of loan application.",
        "application_status": "UNDER_REVIEW",
        "documents": {"present": ["PAYSLIP"], "missing": ["TAX_RETURN"]},
        "key_findings": [
            {"issue": "Missing tax document", "severity": "WARNING", "evidence": ["TAX_RETURN not in uploads"]}
        ],
        "risk_assessment": {
            "ml_probability": 0.45,
            "ml_level": "MEDIUM",
            "evidence_quality": 60.0,
            "review_priority_score": 55.0,
            "review_priority_level": "MEDIUM"
        },
        "policy_basis": [
            {
                "source": "HDFC_INTERNAL_DEMO",
                "is_simulated": True,
                "policy_name": "Simulated Bank Rule — Mandatory Tax Return",
                "relevance": "Underwriting requires tax return for loans exceeding threshold."
            }
        ],
        "missing_information": ["Income Tax Return (ITR)"],
        "investigation_points": ["Request applicant to provide latest Form 16 / ITR."],
        "recommended_next_action": "DOCUMENT_FOLLOWUP",
        "confidence": 0.70
    }

    result = LLMReviewResult(**valid_data)
    assert result.summary == "Concise review of loan application."
    assert result.executive_summary == "Concise review of loan application."
    assert result.recommended_next_action == "DOCUMENT_FOLLOWUP"
    assert result.recommended_action == "DOCUMENT_FOLLOWUP"
    assert result.documents.missing == ["TAX_RETURN"]
    assert result.key_findings[0].severity == "WARNING"


# ── Test 6: Policy source separation ─────────────────────────────────────────

def test_policy_source_separation():
    """
    Ensure system prompt and policy basis enforce distinction between:
    - RBI regulatory requirements (is_simulated=False, source=RBI)
    - HDFC public information (is_simulated=False, source=HDFC_BANK)
    - HDFC simulated demo rules (is_simulated=True, source=HDFC_INTERNAL_DEMO)
    """
    assert "source=\"RBI\", is_simulated=false" in LOAN_REVIEW_SYSTEM_PROMPT
    assert "source=\"HDFC_BANK\", is_simulated=false" in LOAN_REVIEW_SYSTEM_PROMPT
    assert "source=\"HDFC_INTERNAL_DEMO\", is_simulated=true" in LOAN_REVIEW_SYSTEM_PROMPT

    policies = [
        PolicyBasis(source="RBI", is_simulated=False, policy_name="RBI KYC Master Direction", relevance="Mandatory OVD"),
        PolicyBasis(source="HDFC_BANK", is_simulated=False, policy_name="HDFC Bank Public Checklist", relevance="Public docs"),
        PolicyBasis(source="HDFC_INTERNAL_DEMO", is_simulated=True, policy_name="Simulated Salary Variance", relevance="Demo rule"),
    ]

    rbi = [p for p in policies if p.source == "RBI"]
    hdfc_pub = [p for p in policies if p.source == "HDFC_BANK"]
    hdfc_demo = [p for p in policies if p.source == "HDFC_INTERNAL_DEMO"]

    assert len(rbi) == 1 and rbi[0].is_simulated is False
    assert len(hdfc_pub) == 1 and hdfc_pub[0].is_simulated is False
    assert len(hdfc_demo) == 1 and hdfc_demo[0].is_simulated is True


# ── Test 7: Simulated policy labeling ────────────────────────────────────────

def test_simulated_policy_labeling():
    """Verify prompt and policies clearly label simulated rules."""
    assert "Simulated HDFC internal/demo rule" in LOAN_REVIEW_SYSTEM_PROMPT
    assert "Never present simulated rules as official HDFC Bank policy" in LOAN_REVIEW_SYSTEM_PROMPT

    req = LLMDirectReviewRequest(
        application_id="A004",
        retrieved_policies=[
            {
                "source": "HDFC_INTERNAL_DEMO",
                "is_simulated": True,
                "policy_name": "Simulated Bank Rule — Salary Discrepancy",
                "rule": "DEMO_SALARY_VARIANCE_ESCALATION"
            }
        ]
    )
    prompt = format_direct_review_prompt(req)
    assert "[SIMULATED DEMO RULE]" in prompt
    assert "Source=HDFC_INTERNAL_DEMO" in prompt


# ── Test 8: ML risk interpretation ───────────────────────────────────────────

def test_ml_risk_interpretation():
    """
    ML model must be described as 'historical rejection-risk indicator'.
    Must NOT state 'ML says reject' or automatically recommend rejection.
    """
    assert "historical rejection-risk indicator" in LOAN_REVIEW_SYSTEM_PROMPT
    assert "You must NOT state \"ML says reject\"" in LOAN_REVIEW_SYSTEM_PROMPT

    req = LLMDirectReviewRequest(
        application_id="A007",
        ml_risk={"rejection_probability": 0.9556, "risk_level": "HIGH"}
    )
    prompt = format_direct_review_prompt(req)
    assert "Historical Rejection-Risk Indicator" in prompt
    assert "0.9556" in prompt
    assert "HIGH" in prompt


# ── Test 9: Missing document handling ────────────────────────────────────────

def test_missing_document_handling():
    """Missing documents must not be treated as data mismatches."""
    assert "Missing documents must NOT be treated as data mismatches" in LOAN_REVIEW_SYSTEM_PROMPT
    assert "Do not invent contents of missing documents" in LOAN_REVIEW_SYSTEM_PROMPT

    req = LLMDirectReviewRequest(
        application_id="A003",
        documents_present=["PAYSLIP", "BANK_STATEMENT"],
        documents_missing=["TAX_RETURN"]
    )
    prompt = format_direct_review_prompt(req)
    assert "Documents Missing: TAX_RETURN" in prompt


# ── Test 10: Conflicting evidence handling ───────────────────────────────────

def test_conflicting_evidence_handling():
    """When documents conflict, state the conflict and values; do not arbitrarily decide."""
    assert "state the conflict and the exact supplied values" in LOAN_REVIEW_SYSTEM_PROMPT
    assert "Do NOT arbitrarily decide which document is correct" in LOAN_REVIEW_SYSTEM_PROMPT

    req = LLMDirectReviewRequest(
        application_id="A004",
        verification_findings=[
            {
                "rule_name": "RULE_MONTHLY_SALARY_MATCH",
                "result": "MISMATCH",
                "details": "Payslip net salary INR 117,040 vs Bank credit INR 82,000 (variance 29.9%)"
            }
        ]
    )
    prompt = format_direct_review_prompt(req)
    assert "Payslip net salary INR 117,040 vs Bank credit INR 82,000" in prompt


# ── Test 11: Concise response behavior ───────────────────────────────────────

def test_concise_response_behavior():
    """System prompt enforces 1-3 sentences per section and forbids long monologues."""
    assert "Answers must be simple, concise, structured, scannable, factual" in LOAN_REVIEW_SYSTEM_PROMPT
    assert "approximately 1–3 short sentences per section" in LOAN_REVIEW_SYSTEM_PROMPT
    assert "Avoid unnecessary introductory language or conversational monologues" in LOAN_REVIEW_SYSTEM_PROMPT


# ── Test 12: Final-decision safety rule ──────────────────────────────────────

def test_final_decision_safety_rule():
    """
    The LLM must never approve or reject a loan.
    If the LLM attempts to return 'APPROVED' or 'REJECTED', service overrides to 'OFFICER_INVESTIGATION'.
    """
    assert "You do NOT make the final approval or rejection decision" in LOAN_REVIEW_SYSTEM_PROMPT

    # Simulate rogue LLM response trying to reject the loan
    rogue_review = {
        "summary": "Application has discrepancies. Rejecting loan.",
        "application_status": "UNDER_REVIEW",
        "documents": {"present": ["PAYSLIP"], "missing": []},
        "key_findings": [],
        "risk_assessment": {},
        "policy_basis": [],
        "missing_information": [],
        "investigation_points": [],
        "recommended_next_action": "REJECTED",
        "confidence": 0.99
    }

    rogue_provider = FakeLLMProvider(custom_response=json.dumps(rogue_review))
    req = LLMDirectReviewRequest(application_id="APP-ROGUE-001")

    resp = llm_service.generate_direct_review(request=req, provider_override=rogue_provider)

    assert resp.recommended_next_action != "REJECTED"
    assert resp.recommended_next_action == "OFFICER_INVESTIGATION"
    assert resp.recommended_action == "OFFICER_INVESTIGATION"
