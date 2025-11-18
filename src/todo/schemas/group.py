"""Group Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class GroupBase(BaseModel):
    """Base group schema."""

    name: str = Field(..., min_length=1, max_length=100, description="Group name")
    description: str | None = Field(None, max_length=1000, description="Group description")


class GroupCreate(GroupBase):
    """Schema for creating a group."""

    pass


class GroupUpdate(BaseModel):
    """Schema for updating a group."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)


class GroupResponse(GroupBase):
    """Schema for group response."""

    id: int
    created_by_user_id: int
    inserted_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroupListResponse(BaseModel):
    """Schema for group list response."""

    data: list[GroupResponse]


class GroupMemberAdd(BaseModel):
    """Schema for adding a member to a group."""

    user_id: int | None = Field(None, description="User ID to add")
    member_group_id: int | None = Field(None, description="Group ID to add as member")

    @field_validator("user_id", "member_group_id")
    @classmethod
    def validate_exactly_one(cls, v, info):
        """Validate that exactly one of user_id or member_group_id is set."""
        if info.field_name == "member_group_id":
            user_id = info.data.get("user_id")
            if (user_id is None and v is None) or (user_id is not None and v is not None):
                raise ValueError("Exactly one of user_id or member_group_id must be set")
        return v


class GroupMemberResponse(BaseModel):
    """Schema for group member response."""

    id: int
    group_id: int
    user_id: int | None
    member_group_id: int | None
    inserted_at: datetime

    model_config = {"from_attributes": True}


class GroupMembersResponse(BaseModel):
    """Schema for group members list response."""

    data: list[GroupMemberResponse]
