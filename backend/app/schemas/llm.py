"""
LLM Review Schemas — Phase 15 LLM Service

Pydantic schemas for LLM review request, structured output, and API response.
Enforces the Section 15 structured review schema while preserving backward-compatible fields.
"""

from datetime import datetime
from typing import Optional, List, Any, Dict, Union, Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


# ── Granular Component Schemas ──────────────────────────────────────────────

class EvidenceReference(BaseModel):
    """A reference to a specific Evidence Graph node cited by the LLM."""
    node_id: str = Field(..., description="Evidence node ID (e.g. NODE-FIELD-DOC001-name)")
    description: str = Field(..., description="Short human-readable description of the evidence")


class PolicyReference(BaseModel):
    """A reference to a specific Policy Section cited by the LLM."""
    section_id: str = Field(..., description="Policy section ID from Phase 13/14 Knowledge Base")
    policy_name: str = Field(..., description="Name of the policy document")
    authority: str = Field(..., description="RBI, HDFC_BANK, or INTERNAL_RISK_COMMITTEE")
    policy_type: str = Field(..., description="REGULATORY or INTERNAL_UNDERWRITING")
    citation_text: str = Field(..., description="Verbatim or paraphrased text from the policy section")


class DocumentPresence(BaseModel):
    """Present and missing documents summary."""
    present: List[str] = Field(default_factory=list, description="Documents submitted and processed")
    missing: List[str] = Field(default_factory=list, description="Mandatory/expected documents not submitted")


class KeyFinding(BaseModel):
    """A specific factual finding with severity and supporting evidence."""
    issue: str = Field(..., description="Factual issue description")
    severity: Literal["INFO", "WARNING", "ERROR"] = Field("INFO", description="Severity level")
    evidence: List[str] = Field(default_factory=list, description="Specific factual data points supporting this finding")


class RiskAssessment(BaseModel):
    """Integrated risk metrics from ML and deterministic review scoring."""
    ml_probability: Optional[float] = Field(None, description="Historical rejection-risk probability (0.0–1.0)")
    ml_level: Optional[str] = Field(None, description="LOW, MEDIUM, or HIGH historical rejection-risk level")
    evidence_quality: Optional[float] = Field(None, description="Evidence quality/trust score (0–100)")
    review_priority_score: Optional[float] = Field(None, description="Deterministic review priority score (0–100)")
    review_priority_level: Optional[str] = Field(None, description="LOW, MEDIUM, or HIGH review priority")


class PolicyBasis(BaseModel):
    """Policy citation applied in review."""
    source: str = Field(..., description="RBI, HDFC_BANK, or HDFC_INTERNAL_DEMO")
    is_simulated: bool = Field(False, description="True if simulated internal rule; False if official regulation/public guidance")
    policy_name: str = Field(..., description="Policy document title")
    relevance: str = Field(..., description="Concise explanation of policy relevance to the findings")


# ── Request Schemas ─────────────────────────────────────────────────────────

class LLMReviewRequest(BaseModel):
    """Optional request body for POST /applications/{id}/llm/review."""
    force_rebuild: bool = Field(
        False,
        description="If true, re-generates the LLM review even if a cached result exists."
    )
    max_policy_results: int = Field(
        5,
        ge=1,
        le=20,
        description="Maximum number of Policy RAG results to include in context."
    )


class LLMDirectReviewRequest(BaseModel):
    """
    Direct review request for POST /api/v1/llm/review.
    Allows passing direct structured review context without requiring existing DB records,
    or referencing an application_id for automatic compilation.
    """
    application_id: Optional[str] = Field(None, description="Optional application ID to look up or reference")
    applicant_name: Optional[str] = Field(None, description="Applicant full name")
    loan_amount: Optional[float] = Field(None, description="Requested loan amount")
    annual_income: Optional[float] = Field(None, description="Annual declared income")
    monthly_income: Optional[float] = Field(None, description="Monthly declared income")
    cibil_score: Optional[Union[int, str]] = Field(None, description="CIBIL / Credit score")
    documents_present: List[str] = Field(default_factory=list, description="List of document types present")
    documents_missing: List[str] = Field(default_factory=list, description="List of document types missing")
    extracted_fields: Dict[str, Any] = Field(default_factory=dict, description="Extracted key fields per document")
    validation_warnings: List[str] = Field(default_factory=list, description="Document validation warnings/failures")
    verification_findings: List[Dict[str, Any]] = Field(default_factory=list, description="Cross-document verification findings")
    ml_risk: Optional[Dict[str, Any]] = Field(default_factory=dict, description="ML historical rejection-risk details")
    review_score: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Review score and priority details")
    retrieved_policies: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved policy citations from Phase 14 RAG")
    custom_instructions: Optional[str] = Field(None, description="Optional custom review instructions")


# ── Structured LLM Output Result ────────────────────────────────────────────

class LLMReviewResult(BaseModel):
    """
    Structured output produced by the LLM (Phase 15 Section 15 schema).
    The LLM is strictly instructed to return a JSON object matching this schema.
    Provides backward-compatible fields for downstream consumers.
    """
    summary: str = Field(..., description="Concise, 1-3 sentence factual summary of the application review")
    application_status: str = Field("UNDER_REVIEW", description="COMPLETE, INCOMPLETE, or UNDER_REVIEW")
    documents: DocumentPresence = Field(default_factory=DocumentPresence)
    key_findings: List[KeyFinding] = Field(default_factory=list)
    risk_assessment: RiskAssessment = Field(default_factory=RiskAssessment)
    policy_basis: List[PolicyBasis] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    investigation_points: List[str] = Field(default_factory=list)
    recommended_next_action: str = Field(
        "OFFICER_INVESTIGATION",
        description="Suggested next operational step: STANDARD_REVIEW, OFFICER_INVESTIGATION, DOCUMENT_FOLLOWUP, or ESCALATE"
    )
    confidence: Optional[Union[float, str]] = Field(
        None,
        description="Confidence score (0.0-1.0) or qualitative statement ('Insufficient evidence to determine confidence')"
    )

    # ── Backward-compatible fields for existing tests / services ──────────────
    executive_summary: Optional[str] = None
    recommended_action: Optional[str] = None
    confidence_level: Optional[str] = "MEDIUM"
    risk_interpretation: Optional[str] = None
    limitations: List[str] = Field(default_factory=list)
    evidence_references: List[EvidenceReference] = Field(default_factory=list)
    policy_references: List[PolicyReference] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def sync_compatibility_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. Sync summary <-> executive_summary
            if "summary" not in data and "executive_summary" in data:
                data["summary"] = data["executive_summary"]
            elif "executive_summary" not in data and "summary" in data:
                data["executive_summary"] = data["summary"]

            # 2. Sync recommended_next_action <-> recommended_action
            if "recommended_next_action" not in data and "recommended_action" in data:
                data["recommended_next_action"] = data["recommended_action"]
            elif "recommended_action" not in data and "recommended_next_action" in data:
                data["recommended_action"] = data["recommended_next_action"]

            # 3. Normalise string key_findings if provided as list of strings
            raw_findings = data.get("key_findings")
            if isinstance(raw_findings, list) and raw_findings and isinstance(raw_findings[0], str):
                data["key_findings"] = [
                    {"issue": f, "severity": "INFO", "evidence": []} for f in raw_findings
                ]

            # 4. Default risk_interpretation if not supplied
            if "risk_interpretation" not in data:
                risk = data.get("risk_assessment")
                if isinstance(risk, dict) and risk.get("ml_level"):
                    prob = risk.get("ml_probability")
                    prob_str = f" ({prob:.4f})" if prob is not None else ""
                    data["risk_interpretation"] = (
                        f"Historical rejection-risk indicator: {risk.get('ml_level')}{prob_str}."
                    )
                else:
                    data["risk_interpretation"] = "Historical rejection-risk assessment based on Kaggle dataset."

            # 5. Determine confidence_level from confidence if needed
            if "confidence_level" not in data:
                conf = data.get("confidence")
                if isinstance(conf, (int, float)):
                    if conf >= 0.75:
                        data["confidence_level"] = "HIGH"
                    elif conf >= 0.45:
                        data["confidence_level"] = "MEDIUM"
                    else:
                        data["confidence_level"] = "LOW"
                else:
                    data["confidence_level"] = "MEDIUM"
        return data


# ── Full API Response Schema ────────────────────────────────────────────────

class LLMReviewResponse(BaseModel):
    """Full API response for GET/POST /applications/{id}/llm/review and POST /llm/review."""
    model_config = ConfigDict(from_attributes=True)

    review_id: str
    application_id: str
    llm_provider: str
    llm_model: str

    # Structured LLM output fields (Phase 15)
    summary: str
    application_status: str = "UNDER_REVIEW"
    documents: Dict[str, List[str]] = Field(default_factory=lambda: {"present": [], "missing": []})
    key_findings: List[Dict[str, Any]] = Field(default_factory=list)
    risk_assessment: Dict[str, Any] = Field(default_factory=dict)
    policy_basis: List[Dict[str, Any]] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    investigation_points: List[str] = Field(default_factory=list)
    recommended_next_action: str = "OFFICER_INVESTIGATION"
    confidence: Optional[Union[float, str]] = None

    # Backward-compatible fields
    executive_summary: str
    recommended_action: str
    confidence_level: str = "MEDIUM"
    risk_interpretation: str = ""
    limitations: List[str] = Field(default_factory=list)
    evidence_references: List[Dict[str, Any]] = Field(default_factory=list)
    policy_references: List[Dict[str, Any]] = Field(default_factory=list)

    # Grounding & safety status
    grounding_status: str = "GROUNDED"  # GROUNDED, PARTIAL, UNGROUNDED
    injection_check_status: str = "CLEAN"  # CLEAN, FLAGGED

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

