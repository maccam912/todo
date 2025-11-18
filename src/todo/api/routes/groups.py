"""Group routes."""
from fastapi import APIRouter, status

from todo.api.deps import CurrentScope, DatabaseSession
from todo.schemas.group import (
    GroupCreate,
    GroupListResponse,
    GroupMemberAdd,
    GroupMemberResponse,
    GroupMembersResponse,
    GroupResponse,
    GroupUpdate,
)
from todo.services.group_service import (
    add_group_member,
    create_group,
    delete_group,
    get_group_by_id,
    list_group_members,
    list_groups,
    remove_group_member,
    update_group,
)

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=GroupListResponse)
def list_all_groups(db: DatabaseSession):
    """
    List all groups.

    Args:
        db: Database session

    Returns:
        List of groups
    """
    groups = list_groups(db)
    return GroupListResponse(data=groups)


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_new_group(
    group_data: GroupCreate,
    scope: CurrentScope,
    db: DatabaseSession,
):
    """
    Create a new group.

    Args:
        group_data: Group creation data
        scope: Current user scope
        db: Database session

    Returns:
        Created group
    """
    group = create_group(
        db,
        scope,
        name=group_data.name,
        description=group_data.description,
    )
    return group


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    db: DatabaseSession,
):
    """
    Get a specific group.

    Args:
        group_id: Group ID
        db: Database session

    Returns:
        Group
    """
    from fastapi import HTTPException

    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    return group


@router.patch("/{group_id}", response_model=GroupResponse)
@router.put("/{group_id}", response_model=GroupResponse)
def update_existing_group(
    group_id: int,
    group_data: GroupUpdate,
    scope: CurrentScope,
    db: DatabaseSession,
):
    """
    Update a group.

    Args:
        group_id: Group ID
        group_data: Group update data
        scope: Current user scope
        db: Database session

    Returns:
        Updated group
    """
    updates = group_data.model_dump(exclude_none=True)
    group = update_group(db, scope, group_id, updates)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_group(
    group_id: int,
    scope: CurrentScope,
    db: DatabaseSession,
):
    """
    Delete a group.

    Args:
        group_id: Group ID
        scope: Current user scope
        db: Database session
    """
    delete_group(db, scope, group_id)


@router.get("/{group_id}/members", response_model=GroupMembersResponse)
def get_group_members(
    group_id: int,
    db: DatabaseSession,
):
    """
    List all members of a group.

    Args:
        group_id: Group ID
        db: Database session

    Returns:
        List of group members
    """
    members = list_group_members(db, group_id)
    return GroupMembersResponse(data=members)


@router.post("/{group_id}/members", response_model=GroupMemberResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    group_id: int,
    member_data: GroupMemberAdd,
    scope: CurrentScope,
    db: DatabaseSession,
):
    """
    Add a member to a group.

    Args:
        group_id: Group ID
        member_data: Member data
        scope: Current user scope
        db: Database session

    Returns:
        Created membership
    """
    membership = add_group_member(
        db,
        scope,
        group_id,
        user_id=member_data.user_id,
        member_group_id=member_data.member_group_id,
    )
    return membership


@router.delete("/{group_id}/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    group_id: int,
    membership_id: int,
    scope: CurrentScope,
    db: DatabaseSession,
):
    """
    Remove a member from a group.

    Args:
        group_id: Group ID
        membership_id: Membership ID
        scope: Current user scope
        db: Database session
    """
    remove_group_member(db, scope, group_id, membership_id)
