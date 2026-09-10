from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class ReviewFactorSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    factor_type: str  # POSITIVE, NEGATIVE, NEUTRAL
    weight_contribution: float
    impact_points: float
    description: str

class ApplicationReviewScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    review_id: str
    application_id: str
    review_score: float
    review_priority: str  # LOW, MEDIUM, HIGH
    ml_risk_score: Optional[float] = None
    ml_risk_level: Optional[str] = None
    evidence_trust_score: float
    evidence_trust_level: str  # LOW, MEDIUM, HIGH
    evidence_consistency_category: str  # LOW, MEDIUM, HIGH
    primary_reason: Optional[str] = None
    secondary_reasons: List[str] = []
    validation_issue_count: int = 0
    verification_issue_count: int = 0
    document_completeness_status: str = "COMPLETE"
    missing_documents: List[str] = []
    missing_document: Optional[str] = None
    critical_issue: Optional[str] = None
    verification_issue_type: Optional[str] = None
    issue_type: Optional[str] = None
    highest_severity: str = "INFO"
    risk_evidence_matrix_category: str = "CLEAN"  # CLEAN, REVIEW, INVESTIGATE
    score_factors: List[ReviewFactorSchema] = []
    scoring_version: str = "review_score_v1"
    recommended_action: str = "STANDARD_REVIEW"  # STANDARD_REVIEW, OFFICER_INVESTIGATION, DOCUMENT_FOLLOWUP
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
