"""FastAPI dependencies for authentication and database."""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from todo.config import Settings, get_settings
from todo.core.auth import create_scope, verify_api_token
from todo.core.scope import Scope
from todo.database import get_db

# HTTP Bearer token authentication
bearer_scheme = HTTPBearer(auto_error=False)


def _get_user_from_token(
    token: HTTPAuthorizationCredentials | None,
    db: Session,
) -> Any:
    """
    Verify token and return user.

    Args:
        token: Bearer token
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid
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
    return user


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
    """
    user = _get_user_from_token(token, db)
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
    """
    user = _get_user_from_token(token, db)
    return create_scope(db, user, load_preferences=True)


# Type aliases for cleaner dependency injection
CurrentScope = Annotated[Scope, Depends(get_current_user_from_token)]
CurrentScopeWithPrefs = Annotated[Scope, Depends(get_current_user_with_preferences)]
DatabaseSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
