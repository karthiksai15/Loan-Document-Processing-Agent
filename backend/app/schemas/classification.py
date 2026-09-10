from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, ConfigDict

class ClassificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    classified_document_type: str
    confidence: float
    classification_method: str = "KEYWORD_RULES"
    status: str
    matched_signals: List[str] = []
    scores: Dict[str, float] = {}
    error: Optional[str] = None
    classified_at: Optional[datetime] = None
