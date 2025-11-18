"""Authentication routes."""
from fastapi import APIRouter, HTTPException, status

from todo.api.deps import CurrentScope, DatabaseSession
from todo.core.auth import authenticate_user, create_api_token, create_user
from todo.schemas.user import (
    TokenResponse,
    UserAccessTokenCreate,
    UserAccessTokenCreatedResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: DatabaseSession):
    """
    Register a new user.

    Args:
        user_data: User registration data
        db: Database session

    Returns:
        Created user

    Raises:
        HTTPException: If username already exists
    """
    try:
        user = create_user(db, user_data.username, user_data.password)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: DatabaseSession):
    """
    Login and get an API token.

    Args:
        credentials: Login credentials
        db: Database session

    Returns:
        Access token

    Raises:
        HTTPException: If credentials are invalid
    """
    user = authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create API token
    plaintext_token, _ = create_api_token(db, user)

    return TokenResponse(access_token=plaintext_token, token_type="bearer")


@router.post("/tokens", response_model=UserAccessTokenCreatedResponse)
def create_token(
    token_data: UserAccessTokenCreate,
    scope: CurrentScope,
    db: DatabaseSession,
):
    """
    Create a new API access token.

    Args:
        token_data: Token creation data
        scope: Current user scope
        db: Database session

    Returns:
        Created token with plaintext value (shown once)
    """
    plaintext_token, access_token = create_api_token(db, scope.user)

    return UserAccessTokenCreatedResponse(
        id=access_token.id,
        token=plaintext_token,
        token_prefix=access_token.token_prefix,
        inserted_at=access_token.inserted_at,
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(scope: CurrentScope):
    """
    Get current authenticated user.

    Args:
        scope: Current user scope

    Returns:
        Current user
    """
    return scope.user
