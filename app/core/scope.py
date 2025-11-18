"""Scope-based authorization system."""
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Group, GroupMembership, Task, User, UserPreference


@dataclass
class Scope:
    """Authorization scope containing current user and their context."""

    user: User
    preference: UserPreference | None = None


def get_user_group_ids(db: Session, user_id: int, visited: set[int] | None = None) -> set[int]:
    """
    Recursively resolve all groups a user belongs to.

    This handles nested group memberships and prevents infinite loops
    from circular references.

    Args:
        db: Database session
        user_id: User ID to resolve groups for
        visited: Set of already visited group IDs (for recursion)

    Returns:
        Set of all group IDs the user belongs to (direct and nested)
    """
    if visited is None:
        visited = set()

    group_ids = set()

    # Get direct group memberships for this user
    stmt = select(GroupMembership).where(GroupMembership.user_id == user_id)
    direct_memberships = db.execute(stmt).scalars().all()

    for membership in direct_memberships:
        if membership.group_id in visited:
            continue  # Avoid infinite loops

        visited.add(membership.group_id)
        group_ids.add(membership.group_id)

        # Find parent groups that contain this group as a member
        parent_stmt = select(GroupMembership).where(
            GroupMembership.member_group_id == membership.group_id
        )
        parent_memberships = db.execute(parent_stmt).scalars().all()

        for parent_membership in parent_memberships:
            if parent_membership.group_id not in visited:
                # Recursively get parent groups
                parent_ids = _get_parent_group_ids(
                    db, parent_membership.group_id, visited.copy()
                )
                group_ids.update(parent_ids)

    return group_ids


def _get_parent_group_ids(db: Session, group_id: int, visited: set[int]) -> set[int]:
    """
    Helper function to recursively get parent group IDs.

    Args:
        db: Database session
        group_id: Group ID to find parents for
        visited: Set of already visited group IDs

    Returns:
        Set of all parent group IDs
    """
    if group_id in visited:
        return set()

    visited.add(group_id)
    parent_ids = {group_id}

    # Find groups that contain this group as a member
    stmt = select(GroupMembership).where(GroupMembership.member_group_id == group_id)
    parent_memberships = db.execute(stmt).scalars().all()

    for membership in parent_memberships:
        if membership.group_id not in visited:
            parent_ids.update(_get_parent_group_ids(db, membership.group_id, visited))

    return parent_ids


def check_circular_group_reference(
    db: Session, parent_group_id: int, child_group_id: int
) -> bool:
    """
    Check if adding child_group to parent_group would create a circular reference.

    Args:
        db: Database session
        parent_group_id: Group that would contain the child
        child_group_id: Group to be added as member

    Returns:
        True if adding would create a circular reference, False otherwise
    """
    # Get all groups that child_group contains (recursively)
    child_contains = _get_all_member_groups(db, child_group_id, set())

    # If parent_group is in the set of groups that child_group contains,
    # then adding child_group to parent_group would create a cycle
    return parent_group_id in child_contains


def _get_all_member_groups(db: Session, group_id: int, visited: set[int]) -> set[int]:
    """
    Get all groups that are members of the given group (recursively).

    Args:
        db: Database session
        group_id: Group ID to get members for
        visited: Set of already visited group IDs

    Returns:
        Set of all member group IDs
    """
    if group_id in visited:
        return set()

    visited.add(group_id)
    member_ids = {group_id}

    # Get all group members (not user members)
    stmt = select(GroupMembership).where(
        GroupMembership.group_id == group_id,
        GroupMembership.member_group_id.isnot(None),
    )
    memberships = db.execute(stmt).scalars().all()

    for membership in memberships:
        if membership.member_group_id and membership.member_group_id not in visited:
            member_ids.update(
                _get_all_member_groups(db, membership.member_group_id, visited)
            )

    return member_ids


def get_tasks_for_scope(
    db: Session, scope: Scope, status: str | None = None
) -> list[Task]:
    """
    Get all tasks visible to the current user based on scope.

    A user can see a task if:
    - They own it (task.user_id == user.id)
    - They're assigned to it (task.assignee_id == user.id)
    - They're in a group assigned to it (recursively resolved)

    Args:
        db: Database session
        scope: Authorization scope
        status: Optional status filter

    Returns:
        List of tasks visible to the user
    """
    user_id = scope.user.id
    group_ids = get_user_group_ids(db, user_id)

    # Build query
    stmt = (
        select(Task)
        .where(
            or_(
                Task.user_id == user_id,
                Task.assignee_id == user_id,
                Task.assigned_group_id.in_(group_ids) if group_ids else False,
            )
        )
        .options(
            joinedload(Task.blocked_by).joinedload(Task.prerequisite),
            joinedload(Task.blocks).joinedload(Task.blocked_task),
        )
    )

    # Apply status filter if provided
    if status:
        stmt = stmt.where(Task.status == status)

    tasks = db.execute(stmt).unique().scalars().all()
    return list(tasks)


def can_access_task(db: Session, scope: Scope, task: Task) -> bool:
    """
    Check if the user in scope can access the given task.

    Args:
        db: Database session
        scope: Authorization scope
        task: Task to check access for

    Returns:
        True if user can access the task, False otherwise
    """
    user_id = scope.user.id

    # User owns the task
    if task.user_id == user_id:
        return True

    # User is assigned to the task
    if task.assignee_id == user_id:
        return True

    # User is in a group assigned to the task
    if task.assigned_group_id:
        group_ids = get_user_group_ids(db, user_id)
        if task.assigned_group_id in group_ids:
            return True

    return False


def can_modify_task(scope: Scope, task: Task) -> bool:
    """
    Check if the user in scope can modify the given task.

    Only the task owner can modify it.

    Args:
        scope: Authorization scope
        task: Task to check modification rights for

    Returns:
        True if user can modify the task, False otherwise
    """
    return task.user_id == scope.user.id


def can_modify_group(scope: Scope, group: Group) -> bool:
    """
    Check if the user in scope can modify the given group.

    Only the group creator can modify it.

    Args:
        scope: Authorization scope
        group: Group to check modification rights for

    Returns:
        True if user can modify the group, False otherwise
    """
    return group.created_by_user_id == scope.user.id
