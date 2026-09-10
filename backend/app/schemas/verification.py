from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class VerificationFindingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    verification_type: str  # IDENTITY_COMPARISON, INCOME_COMPARISON, SALARY_COMPARISON, DOCUMENT_CONSISTENCY, APPLICATION_DOCUMENT_COMPARISON
    rule_name: str
    source_a: str
    field_a: str
    value_a: Optional[str] = None
    source_b: str
    field_b: str
    value_b: Optional[str] = None
    normalized_value_a: Optional[str] = None
    normalized_value_b: Optional[str] = None
    difference: Optional[float] = None
    difference_percent: Optional[float] = None
    tolerance_percent: Optional[float] = None
    result: str  # MATCH, MISMATCH, NOT_AVAILABLE
    severity: str = "INFO"  # INFO, WARNING, ERROR
    source_document_id: Optional[str] = None
    comparison_document_id: Optional[str] = None
    message: str
    evidence: Optional[str] = None

class ApplicationVerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: str
    status: str  # NOT_VERIFIED, VERIFYING, COMPLETED, FAILED
    overall_result: str  # MATCH, MISMATCHES_FOUND, PASSED_WITH_WARNINGS, INCOMPLETE
    summary: Optional[str] = None
    total_comparisons: int = 0
    matched_comparisons: int = 0
    mismatched_comparisons: int = 0
    unavailable_comparisons: int = 0
    warning_count: int = 0
    error_count: int = 0
    findings: List[VerificationFindingSchema] = []
    error: Optional[str] = None
    verified_at: Optional[datetime] = None
