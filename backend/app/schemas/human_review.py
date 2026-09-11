"""
Human Review & Confidence Schemas — Phase 18 Confidence + Human-in-the-Loop Review

Pydantic schemas for:
- Deterministic confidence evaluation (0-100 scale, explainable factor breakdown)
- Human Review Gate status and reasons
- Officer actions (acknowledge, notes, document request, decision)
- AI recommendation vs human decision separation and override mechanism
- Privacy-safe audit trail
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ConfidenceFactorDetail(BaseModel):
    """Explainable breakdown item for a single confidence factor."""
    name: str = Field(..., description="Factor identifier (e.g., evidence_sufficiency, document_completeness)")
    score: float = Field(..., ge=0.0, le=100.0, description="Raw factor score (0-100)")
    weight: float = Field(..., ge=0.0, le=100.0, description="Factor weight in percentage (0-100)")
    weighted_score: float = Field(..., ge=0.0, le=100.0, description="Score multiplied by weight")
    contribution_pct: float = Field(..., ge=0.0, le=100.0, description="Contribution to the final score")
    explanation: str = Field(..., description="Explainable description of the factor assessment")


class ConfidenceEvaluationSchema(BaseModel):
    """Complete confidence evaluation result."""
    score: float = Field(..., ge=0.0, le=100.0, description="Deterministic confidence score (0-100)")
    level: str = Field(..., description="LOW, MEDIUM, or HIGH")
    breakdown: List[ConfidenceFactorDetail] = Field(default_factory=list, description="Factor-by-factor breakdown")
    penalties_applied: List[str] = Field(default_factory=list, description="Any hard caps or penalties triggered")


class HumanReviewReason(BaseModel):
    """Structured reason why an application requires human review."""
    code: str = Field(..., description="Standard reason code (e.g. IDENTITY_MISMATCH, LOW_CONFIDENCE)")
    severity: str = Field(..., description="ERROR or WARNING")
    description: str = Field(..., description="Detailed description of the trigger")


class OfficerNoteSchema(BaseModel):
    """A timestamped note added by a loan officer."""
    note_id: str = Field(..., description="Unique note identifier")
    officer_id: str = Field(..., description="Loan officer identifier")
    text: str = Field(..., description="Content of the note")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class RequestedDocumentItem(BaseModel):
    """A document follow-up requested by a loan officer."""
    doc_type: str = Field(..., description="Type of document requested (e.g. PAYSLIP, BANK_STATEMENT)")
    reason: str = Field(..., description="Reason for the document request")
    requested_by: str = Field(..., description="Loan officer identifier")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class HumanReviewGateResponse(BaseModel):
    """Full response for Human Review Gate status and current review state."""
    model_config = ConfigDict(from_attributes=True)

    application_id: str
    review_action_id: str
    agent_review_id: Optional[str] = None
    ai_recommendation: str
    confidence_score: float
    confidence_level: str
    confidence_factors: List[Dict[str, Any]] = []
    human_review_required: bool
    human_review_status: str  # NOT_REQUIRED, REQUIRED, IN_REVIEW, COMPLETED, OVERRIDDEN
    reasons: List[HumanReviewReason] = []
    human_decision: Optional[str] = None
    override: bool = False
    override_reason: Optional[str] = None
    decision_reason: Optional[str] = None
    officer_notes: List[OfficerNoteSchema] = []
    requested_documents: List[RequestedDocumentItem] = []
    officer_feedback: List[Dict[str, Any]] = []
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str
    updated_at: str


class AcknowledgeReviewRequest(BaseModel):
    """Request to acknowledge a required review."""
    officer_id: Optional[str] = Field(default=None, description="Loan officer identifier acknowledging the review")


class OfficerNoteRequest(BaseModel):
    """Request to append an officer note."""
    officer_id: Optional[str] = Field(default=None, description="Loan officer identifier")
    note: str = Field(..., min_length=1, description="Officer note text")


class RequestDocumentsRequest(BaseModel):
    """Request to request additional documents from the applicant."""
    officer_id: Optional[str] = Field(default=None, description="Loan officer identifier")
    documents: List[str] = Field(..., min_length=1, description="List of document types requested")
    reason: str = Field(..., min_length=1, description="Reason for requesting these documents")


class HumanDecisionRequest(BaseModel):
    """
    Request to record a final human decision on the loan application.
    Enforces that override_reason is provided if human_decision != ai_recommendation.
    Requires decision_reason for APPROVED and REJECTED decisions.
    """
    officer_id: Optional[str] = Field(default=None, description="Loan officer identifier")
    decision: str = Field(
        ...,
        description="Human decision: APPROVED, REJECTED, OFFICER_INVESTIGATION, DOCUMENT_FOLLOWUP, or ESCALATED"
    )
    decision_reason: Optional[str] = Field(
        None,
        description="Rationale for the decision. Required for APPROVED and REJECTED."
    )
    override_reason: Optional[str] = Field(
        None,
        description="Mandatory if decision deviates from the AI recommendation"
    )
    notes: Optional[str] = Field(
        None,
        description="Optional accompanying officer notes"
    )


class OfficerFeedbackItem(BaseModel):
    """Structured officer feedback item."""
    feedback_id: str
    officer_id: str
    feedback: str
    category: Optional[str] = None  # CORRECT, PARTIALLY_CORRECT, INCORRECT, NOT_APPLICABLE
    timestamp: str


class OfficerFeedbackRequest(BaseModel):
    """Request body for submitting loan officer feedback."""
    officer_id: str = Field(..., min_length=1, description="Loan officer identifier")
    feedback: str = Field(..., min_length=1, max_length=2000, description="Officer feedback commentary")
    category: Optional[str] = Field(
        None,
        description="Optional feedback classification: CORRECT, PARTIALLY_CORRECT, INCORRECT, NOT_APPLICABLE"
    )


class DecisionHistoryResponse(BaseModel):
    """Full decision history response for an application."""
    application_id: str
    ai_recommendation: str
    human_decision: Optional[str] = None
    alignment_status: str  # ALIGNED, OVERRIDDEN, PENDING
    decision_reason: Optional[str] = None
    override_reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    feedback: List[OfficerFeedbackItem] = []
    timestamp: Optional[str] = None
    history: List[Dict[str, Any]] = []


class HumanReviewAuditItem(BaseModel):
    """A single audit trail event."""
    model_config = ConfigDict(from_attributes=True)

    audit_id: str
    application_id: str
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    actor_type: str  # SYSTEM, LOAN_OFFICER
    actor_id: str
    note: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: str


class HumanReviewAuditResponse(BaseModel):
    """Response containing the chronological audit trail for an application."""
    application_id: str
    total_events: int
    events: List[HumanReviewAuditItem] = []
