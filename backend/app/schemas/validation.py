from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ValidationCheckSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    check_name: str
    severity: str = "INFO"  # INFO, WARNING, ERROR
    status: str = "PASS"    # PASS, WARNING, FAIL, NOT_CHECKED
    message: str
    field_name: Optional[str] = None
    evidence: Optional[str] = None

class DocumentValidationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    classified_document_type: str
    status: str
    overall_result: str  # PASS, PASS_WITH_WARNINGS, FAIL, UNSUPPORTED
    summary: Optional[str] = None
    total_checks: int = 0
    passed_checks: int = 0
    warning_checks: int = 0
    failed_checks: int = 0
    checks: List[ValidationCheckSchema] = []
    error: Optional[str] = None
    validated_at: Optional[datetime] = None
