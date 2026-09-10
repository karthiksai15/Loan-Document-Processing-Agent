from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class ApplicationRiskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: str
    model_name: str
    model_version: str = "v1"
    rejection_probability: float = 0.0
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH
    prediction: int = 0  # 1 = historical rejected outcome, 0 = historical approved outcome
    target_definition: str = "historical_rejection_outcome"
    feature_version: str = "v1"
    status: str = "COMPLETED"  # COMPLETED, UNAVAILABLE
    missing_features: List[str] = []
    reason: Optional[str] = None
    generated_at: Optional[datetime] = None
