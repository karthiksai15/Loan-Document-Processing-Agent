from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class ApplicationCreate(BaseModel):
    applicant_name: str = Field(..., json_schema_extra={"example": "Aarav Sharma"}, min_length=1)
    loan_amount: Optional[float] = Field(default=0.0, ge=0.0)
    application_id: Optional[str] = Field(default=None, description="Custom application ID (e.g. A001). Auto-generated if omitted.")

class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: str
    application_number: Optional[str] = None
    user_id: Optional[str] = None
    applicant_name: str
    loan_amount: float
    status: str
    created_at: datetime
    updated_at: datetime
    documents_count: int = 0
    cibil_score: Optional[int] = None
    income_annum: Optional[float] = None
    employer: Optional[str] = None
    education: Optional[str] = None
    self_employed: Optional[str] = None
    loan_term: Optional[int] = None
    scenario: Optional[str] = None
    ml_risk_score: Optional[float] = None
    ml_risk_level: Optional[str] = None
    evidence_trust_score: Optional[float] = None
    evidence_trust_level: Optional[str] = None
    review_priority: Optional[str] = None
    primary_reason: Optional[str] = None
    human_review_required: Optional[bool] = None
    human_review_status: Optional[str] = None
    is_demo: bool = False

class ApplicationListResponse(BaseModel):
    total: int
    applications: List[ApplicationResponse]

class AttentionItem(BaseModel):
    application_id: str
    applicant_name: str
    loan_amount: float
    ml_risk_level: str
    evidence_trust_level: str
    review_priority: str
    human_review_status: str
    primary_issue: str
    scenario: Optional[str] = None

class DashboardOverviewResponse(BaseModel):
    total_applications: int
    review_required_count: int
    high_priority_count: int
    documents_pending_count: int
    completed_count: int
    attention_queue: List[AttentionItem]
