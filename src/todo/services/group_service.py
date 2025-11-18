"""Group service for managing groups and memberships."""

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from todo.core.scope import Scope, can_modify_group, check_circular_group_reference
from todo.models import Group, GroupMembership


def create_group(
    db: Session,
    scope: Scope,
    name: str,
    description: str | None = None,
) -> Group:
    """
    Create a new group.

    Args:
        db: Database session
        scope: Authorization scope
        name: Group name
        description: Group description

    Returns:
        Created group

    Raises:
        HTTPException: If group name already exists
    """
    # Check if name already exists
    stmt = select(Group).where(Group.name == name)
    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group name already exists",
        )

    group = Group(
        name=name,
        description=description,
        created_by_user_id=scope.user.id,
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    return group


def get_group_by_id(db: Session, group_id: int) -> Group | None:
    """
    Get a group by ID.

    Args:
        db: Database session
        group_id: Group ID

    Returns:
        Group if found, None otherwise
    """
    stmt = select(Group).where(Group.id == group_id)
    return db.execute(stmt).scalar_one_or_none()


def list_groups(db: Session) -> list[Group]:
    """
    List all groups.

    Args:
        db: Database session

    Returns:
        List of all groups
    """
    stmt = select(Group)
    return list(db.execute(stmt).scalars().all())


def update_group(
    db: Session,
    scope: Scope,
    group_id: int,
    updates: dict[str, Any],
) -> Group:
    """
    Update a group.

    Args:
        db: Database session
        scope: Authorization scope
        group_id: Group ID
        updates: Dictionary of fields to update

    Returns:
        Updated group

    Raises:
        HTTPException: If group not found, unauthorized, or validation fails
    """
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    if not can_modify_group(scope, group):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this group",
        )

    # Check if name is being updated to an existing name
    if "name" in updates and updates["name"] != group.name:
        stmt = select(Group).where(Group.name == updates["name"])
        existing = db.execute(stmt).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group name already exists",
            )

    # Update fields
    for field, value in updates.items():
        if value is not None and hasattr(group, field):
            setattr(group, field, value)

    group.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(group)

    return group


def delete_group(db: Session, scope: Scope, group_id: int) -> None:
    """
    Delete a group.

    Args:
        db: Database session
        scope: Authorization scope
        group_id: Group ID

    Raises:
        HTTPException: If group not found or unauthorized
    """
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    if not can_modify_group(scope, group):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this group",
        )

    db.delete(group)
    db.commit()


def add_group_member(
    db: Session,
    scope: Scope,
    group_id: int,
    user_id: int | None = None,
    member_group_id: int | None = None,
) -> GroupMembership:
    """
    Add a member to a group.

    Args:
        db: Database session
        scope: Authorization scope
        group_id: Group ID
        user_id: User ID to add (mutually exclusive with member_group_id)
        member_group_id: Group ID to add as member (mutually exclusive with user_id)

    Returns:
        Created group membership

    Raises:
        HTTPException: If validation fails or would create circular reference
    """
    # Validate exactly one of user_id or member_group_id is set
    if (user_id is None and member_group_id is None) or (
        user_id is not None and member_group_id is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly one of user_id or member_group_id must be set",
        )

    # Get group and check authorization
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    if not can_modify_group(scope, group):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this group",
        )

    # Check if member already exists
    stmt = select(GroupMembership).where(GroupMembership.group_id == group_id)
    if user_id:
        stmt = stmt.where(GroupMembership.user_id == user_id)
    else:
        stmt = stmt.where(GroupMembership.member_group_id == member_group_id)

    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member already exists in group",
        )

    # If adding a group member, check for circular references
    if member_group_id:
        # Verify member group exists
        member_group = get_group_by_id(db, member_group_id)
        if not member_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member group not found",
            )

        # Check for circular reference
        if check_circular_group_reference(db, group_id, member_group_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Adding this group would create a circular reference",
            )

    # Create membership
    membership = GroupMembership(
        group_id=group_id,
        user_id=user_id,
        member_group_id=member_group_id,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return membership


def remove_group_member(
    db: Session,
    scope: Scope,
    group_id: int,
    membership_id: int,
) -> None:
    """
    Remove a member from a group.

    Args:
        db: Database session
        scope: Authorization scope
        group_id: Group ID
        membership_id: Membership ID to remove

    Raises:
        HTTPException: If membership not found or unauthorized
    """
    # Get group and check authorization
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    if not can_modify_group(scope, group):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this group",
        )

    # Get membership
    stmt = select(GroupMembership).where(
        GroupMembership.id == membership_id,
        GroupMembership.group_id == group_id,
    )
    membership = db.execute(stmt).scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    db.delete(membership)
    db.commit()


def list_group_members(db: Session, group_id: int) -> list[GroupMembership]:
    """
    List all members of a group.

    Args:
        db: Database session
        group_id: Group ID

    Returns:
        List of group memberships

    Raises:
        HTTPException: If group not found
    """
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    stmt = select(GroupMembership).where(GroupMembership.group_id == group_id)
    return list(db.execute(stmt).scalars().all())
