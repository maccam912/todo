"""Authentication utilities."""
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import Settings
from app.core.scope import Scope
from app.core.security import (
    generate_access_token,
    generate_session_token,
    hash_access_token,
    hash_password,
    is_session_token_expired,
    should_rotate_session_token,
    verify_password,
)
from app.models import User, UserAccessToken, UserPreference, UserToken


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """
    Authenticate a user by username and password.

    Args:
        db: Database session
        username: Username
        password: Plaintext password

    Returns:
        User object if authentication successful, None otherwise
    """
    stmt = select(User).where(User.username == username)
    user = db.execute(stmt).scalar_one_or_none()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def create_user(db: Session, username: str, password: str) -> User:
    """
    Create a new user.

    Args:
        db: Database session
        username: Username
        password: Plaintext password

    Returns:
        Created user object
    """
    # Check if username already exists
    stmt = select(User).where(User.username == username)
    existing_user = db.execute(stmt).scalar_one_or_none()
    if existing_user:
        raise ValueError("Username already exists")

    # Create user
    hashed_pw = hash_password(password)
    user = User(username=username, hashed_password=hashed_pw)
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_session_token(db: Session, user: User) -> bytes:
    """
    Create a session token for a user.

    Args:
        db: Database session
        user: User to create token for

    Returns:
        Token bytes
    """
    token = generate_session_token()

    user_token = UserToken(
        user_id=user.id,
        token=token,
        context="session",
        authenticated_at=datetime.now(UTC),
    )
    db.add(user_token)
    db.commit()

    return token


def verify_session_token(
    db: Session, token: bytes, settings: Settings
) -> tuple[User, UserToken] | None:
    """
    Verify a session token and return the associated user.

    Args:
        db: Database session
        token: Token bytes
        settings: Application settings

    Returns:
        Tuple of (User, UserToken) if valid, None otherwise
    """
    stmt = (
        select(UserToken)
        .where(UserToken.token == token, UserToken.context == "session")
        .options(joinedload(UserToken.user))
    )
    user_token = db.execute(stmt).scalar_one_or_none()

    if not user_token:
        return None

    # Check if token has expired
    if is_session_token_expired(user_token.inserted_at, settings):
        db.delete(user_token)
        db.commit()
        return None

    # Check if token should be rotated
    if should_rotate_session_token(user_token.inserted_at, settings):
        # Create new token
        new_token_bytes = generate_session_token()
        new_user_token = UserToken(
            user_id=user_token.user_id,
            token=new_token_bytes,
            context="session",
            authenticated_at=datetime.now(UTC),
        )
        db.add(new_user_token)

        # Delete old token
        db.delete(user_token)
        db.commit()
        db.refresh(new_user_token)

        return new_user_token.user, new_user_token

    return user_token.user, user_token


def create_api_token(db: Session, user: User) -> tuple[str, UserAccessToken]:
    """
    Create an API access token for a user.

    Args:
        db: Database session
        user: User to create token for

    Returns:
        Tuple of (plaintext_token, UserAccessToken)
    """
    plaintext_token, token_hash, token_prefix = generate_access_token()

    access_token = UserAccessToken(
        user_id=user.id,
        token_hash=token_hash,
        token_prefix=token_prefix,
    )
    db.add(access_token)
    db.commit()
    db.refresh(access_token)

    return plaintext_token, access_token


def verify_api_token(db: Session, token: str) -> User | None:
    """
    Verify an API access token and return the associated user.

    Args:
        db: Database session
        token: Plaintext token

    Returns:
        User if valid, None otherwise
    """
    token_hash = hash_access_token(token)

    stmt = (
        select(UserAccessToken)
        .where(UserAccessToken.token_hash == token_hash)
        .options(joinedload(UserAccessToken.user))
    )
    access_token = db.execute(stmt).scalar_one_or_none()

    if not access_token:
        return None

    return access_token.user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """
    Get a user by ID.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        User if found, None otherwise
    """
    stmt = select(User).where(User.id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def create_scope(db: Session, user: User, load_preferences: bool = False) -> Scope:
    """
    Create an authorization scope for a user.

    Args:
        db: Database session
        user: User
        load_preferences: Whether to load user preferences

    Returns:
        Scope object
    """
    preference = None
    if load_preferences:
        stmt = select(UserPreference).where(UserPreference.user_id == user.id)
        preference = db.execute(stmt).scalar_one_or_none()

    return Scope(user=user, preference=preference)


def update_password(
    db: Session, user: User, current_password: str, new_password: str
) -> None:
    """
    Update a user's password.

    Args:
        db: Database session
        user: User to update password for
        current_password: Current plaintext password
        new_password: New plaintext password

    Raises:
        HTTPException: If current password is incorrect
    """
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Update password
    user.hashed_password = hash_password(new_password)
    user.updated_at = datetime.now(UTC)

    # Delete all session tokens except current one (handled by caller)
    # Delete all API tokens (user needs to regenerate them)
    stmt = select(UserAccessToken).where(UserAccessToken.user_id == user.id)
    tokens = db.execute(stmt).scalars().all()
    for token in tokens:
        db.delete(token)

    db.commit()
