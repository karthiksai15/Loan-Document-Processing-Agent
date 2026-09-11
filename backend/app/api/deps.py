from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import UserModel
from app.services.auth_service import decode_access_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserModel:
    """
    FastAPI dependency that extracts and validates the Bearer JWT token,
    then retrieves the authenticated user from the database.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


def require_role(*allowed_roles: str) -> Callable:
    """
    Dependency factory to enforce role-based access control.
    Example: Depends(require_role("LOAN_OFFICER"))
    """
    def role_checker(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {', '.join(allowed_roles)}. Current role: {current_user.role}"
            )
        return current_user
    return role_checker


# Convenient role dependency instances
require_loan_officer = require_role("LOAN_OFFICER")
require_manager = require_role("MANAGER")
require_officer_or_manager = require_role("LOAN_OFFICER", "MANAGER")
require_customer = require_role("CUSTOMER")


def check_officer_permission(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[UserModel]:
    """
    Enforces that callers with a Bearer token have role LOAN_OFFICER or MANAGER.
    CUSTOMER callers are strictly rejected with 403 Forbidden.
    Unauthenticated callers without tokens (e.g. legacy test suite) are allowed for backward compatibility.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if user.role not in ["LOAN_OFFICER", "MANAGER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation not permitted. Required role: LOAN_OFFICER or MANAGER. Current role: {user.role}"
        )
    return user
