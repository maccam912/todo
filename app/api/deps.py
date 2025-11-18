"""FastAPI dependencies for authentication and database."""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.auth import create_scope, verify_api_token
from app.core.scope import Scope
from app.database import get_db

# HTTP Bearer token authentication
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_from_token(
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Scope:
    """
    Get current user from Bearer token.

    Args:
        token: Bearer token from Authorization header
        db: Database session

    Returns:
        Scope object with current user

    Raises:
        HTTPException: If token is invalid or missing
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = verify_api_token(db, token.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return create_scope(db, user, load_preferences=False)


def get_current_user_with_preferences(
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Scope:
    """
    Get current user with preferences from Bearer token.

    Args:
        token: Bearer token from Authorization header
        db: Database session

    Returns:
        Scope object with current user and preferences

    Raises:
        HTTPException: If token is invalid or missing
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = verify_api_token(db, token.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return create_scope(db, user, load_preferences=True)


# Type aliases for cleaner dependency injection
CurrentScope = Annotated[Scope, Depends(get_current_user_from_token)]
CurrentScopeWithPrefs = Annotated[Scope, Depends(get_current_user_with_preferences)]
DatabaseSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
