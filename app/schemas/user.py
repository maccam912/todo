"""User Pydantic schemas."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class UserBase(BaseModel):
    """Base user schema."""

    username: str = Field(
        ..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_.-]+$",
        description="Username (3-32 chars, alphanumeric + _ . -)"
    )


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(
        ..., min_length=12, max_length=72, description="Password (12-72 characters)"
    )


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(default=False, description="Remember me for 14 days")


class UserResponse(UserBase):
    """Schema for user response."""

    id: int
    inserted_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserPreferenceBase(BaseModel):
    """Base user preference schema."""

    prompt_preferences: str | None = Field(
        None, max_length=2000, description="Custom LLM instructions"
    )


class UserPreferenceCreate(UserPreferenceBase):
    """Schema for creating user preferences."""

    pass


class UserPreferenceUpdate(UserPreferenceBase):
    """Schema for updating user preferences."""

    pass


class UserPreferenceResponse(UserPreferenceBase):
    """Schema for user preference response."""

    id: int
    user_id: int
    inserted_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    token_type: str = "bearer"


class UserAccessTokenCreate(BaseModel):
    """Schema for creating an access token."""

    pass


class UserAccessTokenResponse(BaseModel):
    """Schema for access token response."""

    id: int
    token_prefix: str
    inserted_at: datetime

    model_config = {"from_attributes": True}


class UserAccessTokenCreatedResponse(BaseModel):
    """Schema for newly created access token with plaintext token."""

    id: int
    token: str  # Only shown once
    token_prefix: str
    inserted_at: datetime

    model_config = {"from_attributes": True}


class PasswordUpdate(BaseModel):
    """Schema for password update."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ..., min_length=12, max_length=72, description="New password (12-72 characters)"
    )
