from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ExtractedFieldSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_name: str
    raw_value: Optional[str] = None
    normalized_value: Optional[str] = None
    field_type: str = "string"
    confidence: float = 0.95
    extraction_method: str = "LABEL_PATTERN"
    evidence: Optional[str] = None

class ExtractedFieldsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    classified_document_type: str
    status: str
    fields_count: int = 0
    fields: List[ExtractedFieldSchema] = []
    error: Optional[str] = None
    extracted_at: Optional[datetime] = None
