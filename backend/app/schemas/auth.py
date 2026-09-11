from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., description="Google ID Token (JWT) issued by Google Identity Services")
    role: Optional[str] = Field(
        default=None,
        description="Optional preferred initial role ('CUSTOMER' or 'LOAN_OFFICER') for new accounts"
    )

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    picture_url: Optional[str] = None
    role: str
    created_at: datetime
    updated_at: Optional[datetime] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
