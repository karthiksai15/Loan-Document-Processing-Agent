from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    status: str
    method: Optional[str] = None
    character_count: int = 0
    text: Optional[str] = None
    error: Optional[str] = None
    processed_at: Optional[datetime] = None
