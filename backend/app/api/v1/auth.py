from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import UserModel
from app.api.deps import get_current_user
from app.schemas.auth import GoogleAuthRequest, UserResponse, TokenResponse
from app.services.auth_service import authenticate_google_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/google",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate with Google Identity Services"
)
def auth_with_google(
    payload: GoogleAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Exchanges a Google ID Token (JWT) from Google Identity Services for a GenBank backend session.
    Verifies token with Google, creates or updates the user profile, and returns a backend JWT.
    """
    user, token = authenticate_google_user(
        db=db,
        id_token_str=payload.id_token,
        role_preference=payload.role
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile"
)
def get_me(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Returns the authenticated user's profile details.
    Requires a valid Bearer JWT access token in the Authorization header.
    """
    return UserResponse.model_validate(current_user)
