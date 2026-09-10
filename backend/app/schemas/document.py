from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    application_id: str
    original_filename: str
    stored_filename: str
    document_type: str
    mime_type: str
    file_size: int
    checksum: str
    processing_status: str
    uploaded_at: datetime

class DocumentListResponse(BaseModel):
    application_id: str
    total: int
    documents: List[DocumentResponse]
