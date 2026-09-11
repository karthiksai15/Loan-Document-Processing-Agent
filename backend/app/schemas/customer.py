from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class CustomerApplicationCreate(BaseModel):
    applicant_name: str = Field(..., min_length=2, max_length=255, description="Borrower full legal name")
    loan_amount: float = Field(..., gt=0, description="Requested loan principal amount")
    income_annum: Optional[float] = Field(default=None, ge=0, description="Gross annual income")
    employer: Optional[str] = Field(default=None, max_length=255, description="Current employer or business name")
    loan_term: Optional[int] = Field(default=12, ge=1, le=360, description="Loan term in months")
    date_of_birth: Optional[str] = Field(default=None, max_length=50, description="Date of birth (YYYY-MM-DD)")
    address: Optional[str] = Field(default=None, description="Residential address")
    education: Optional[str] = Field(default="Graduate", max_length=100, description="Education level")
    self_employed: Optional[str] = Field(default="No", description="Self-employed status ('Yes' or 'No')")
    notes: Optional[str] = Field(default=None, description="Additional loan application details or remarks")


class CustomerDocumentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    document_type: str
    original_filename: str
    file_size: int
    uploaded_at: datetime
    processing_status: str


class CustomerApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: str
    application_number: Optional[str] = None
    applicant_name: str
    loan_amount: float
    income_annum: Optional[float] = None
    employer: Optional[str] = None
    loan_term: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime
    documents_count: int = 0
    documents: List[CustomerDocumentItem] = []


class CustomerApplicationListResponse(BaseModel):
    total: int
    applications: List[CustomerApplicationResponse]


class CustomerSubmitResponse(BaseModel):
    application_id: str
    application_number: str
    status: str
    message: str
