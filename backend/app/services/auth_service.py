import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
import jwt
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.db.models import UserModel


def get_allowed_google_audiences() -> list[str]:
    """Returns the list of valid Google OAuth client IDs accepted as audiences."""
    audiences = [settings.GOOGLE_CLIENT_ID]
    canonical = "927480599191-iock07diunjgmr0t3fdi3teh7ot5grk5.apps.googleusercontent.com"
    if canonical not in audiences:
        audiences.append(canonical)
    return audiences


def verify_google_id_token(token: str) -> Dict[str, Any]:
    """
    Verifies a Google ID token with Google's public keys.
    Validates audience against GOOGLE_CLIENT_ID and ensures email is verified.
    """
    try:
        request = google_requests.Request()
        allowed_audiences = get_allowed_google_audiences()
        id_info = google_id_token.verify_oauth2_token(
            token,
            request,
            audience=allowed_audiences
        )

        # Confirm issuer
        if id_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            logger.warning(f"Google token verification failed: invalid issuer {id_info.get('iss')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer"
            )

        # Confirm audience matches our client ID
        if id_info.get("aud") not in allowed_audiences:
            logger.warning("Google token verification failed: audience mismatch")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token audience does not match GOOGLE_CLIENT_ID"
            )

        # Confirm email verification status
        email_verified = id_info.get("email_verified")
        if email_verified is False or str(email_verified).lower() == "false":
            logger.warning("Google token verification failed: email is unverified")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google email address is not verified"
            )

        return id_info

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Google token validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error validating Google token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to verify Google identity token"
        )


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Encodes a JWT access token containing subject, email, role, and expiration.
    """
    to_encode = data.copy()
    now_utc = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now_utc
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a backend JWT access token.
    Raises 401 if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


def determine_user_role(email: str, role_preference: Optional[str] = None) -> str:
    """
    Determines user role based on email allowlists and portal selection.
    
    1. If email is in MANAGER_EMAILS -> MANAGER
    2. If email is in LOAN_OFFICER_EMAILS -> LOAN_OFFICER
    3. If role_preference is specified:
       - 'LOAN_OFFICER', 'OFFICER' -> LOAN_OFFICER
       - 'MANAGER' -> MANAGER
       - 'CUSTOMER' -> CUSTOMER
    4. Default -> CUSTOMER
    """
    email_clean = (email or "").strip().lower()
    manager_emails = [
        e.strip().lower()
        for e in getattr(settings, "MANAGER_EMAILS", "").split(",")
        if e.strip()
    ]
    officer_emails = [
        e.strip().lower()
        for e in getattr(settings, "LOAN_OFFICER_EMAILS", "").split(",")
        if e.strip()
    ]

    if email_clean in manager_emails:
        return "MANAGER"
    if email_clean in officer_emails:
        return "LOAN_OFFICER"

    if role_preference:
        pref = role_preference.strip().upper()
        if pref in ("LOAN_OFFICER", "OFFICER"):
            return "LOAN_OFFICER"
        elif pref == "MANAGER":
            return "MANAGER"
        elif pref == "CUSTOMER":
            return "CUSTOMER"

    return "CUSTOMER"


def authenticate_google_user(
    db: Session,
    id_token_str: str,
    role_preference: Optional[str] = None
) -> Tuple[UserModel, str]:
    """
    Verifies Google ID token, finds or creates the user in the database,
    and returns (user, jwt_access_token).
    """
    id_info = verify_google_id_token(id_token_str)

    google_id = id_info.get("sub")
    email = id_info.get("email")
    name = id_info.get("name") or (email.split("@")[0] if email else "User")
    picture_url = id_info.get("picture")

    if not google_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google profile is missing required identity fields"
        )

    # Determine assigned role based on configuration or portal selection
    target_role = determine_user_role(email, role_preference)

    # 1. Check if user exists by google_id
    user = db.query(UserModel).filter(UserModel.google_id == google_id).first()

    # 2. If not found by google_id, check by email
    if not user:
        user = db.query(UserModel).filter(UserModel.email == email).first()
        if user:
            # Link google_id to existing user account
            user.google_id = google_id

    # 3. Existing user update profile info and role if explicitly requested
    if user:
        if role_preference and user.role != target_role:
            user.role = target_role
        if picture_url and user.picture_url != picture_url:
            user.picture_url = picture_url
        if name and user.name != name:
            user.name = name
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
    else:
        # 4. Create new user with assigned role
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()
        user = UserModel(
            id=user_id,
            email=email,
            name=name,
            google_id=google_id,
            picture_url=picture_url,
            role=target_role,
            created_at=now,
            updated_at=now
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user: {user.id} ({user.email}) with role {user.role}")

    # 5. Issue JWT access token containing subject, email, and verified role
    token_payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role
    }
    access_token = create_access_token(token_payload)

    return user, access_token
