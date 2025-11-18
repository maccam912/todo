"""Pydantic schemas for request/response validation."""
from todo.schemas.group import (
    GroupCreate,
    GroupListResponse,
    GroupMemberAdd,
    GroupMemberResponse,
    GroupMembersResponse,
    GroupResponse,
    GroupUpdate,
)
from todo.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskProcessRequest,
    TaskProcessResponse,
    TaskResponse,
    TaskUpdate,
)
from todo.schemas.user import (
    PasswordUpdate,
    TokenResponse,
    UserAccessTokenCreate,
    UserAccessTokenCreatedResponse,
    UserAccessTokenResponse,
    UserCreate,
    UserLogin,
    UserPreferenceCreate,
    UserPreferenceResponse,
    UserPreferenceUpdate,
    UserResponse,
)

__all__ = [
    # User schemas
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "UserPreferenceCreate",
    "UserPreferenceUpdate",
    "UserPreferenceResponse",
    "UserAccessTokenCreate",
    "UserAccessTokenResponse",
    "UserAccessTokenCreatedResponse",
    "PasswordUpdate",
    # Task schemas
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "TaskListResponse",
    "TaskProcessRequest",
    "TaskProcessResponse",
    # Group schemas
    "GroupCreate",
    "GroupUpdate",
    "GroupResponse",
    "GroupListResponse",
    "GroupMemberAdd",
    "GroupMemberResponse",
    "GroupMembersResponse",
]
