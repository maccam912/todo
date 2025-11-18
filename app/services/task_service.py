"""Task service for CRUD operations and business logic."""
from datetime import UTC, date, datetime
from typing import Any

from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.scope import Scope, can_access_task, can_modify_task, get_tasks_for_scope
from app.models import Task, TaskDependency, TaskRecurrence, TaskStatus


def create_task(
    db: Session,
    scope: Scope,
    title: str,
    description: str | None = None,
    notes: str | None = None,
    task_status: TaskStatus = TaskStatus.TODO,
    urgency: str = "normal",
    due_date: date | None = None,
    deferred_until: date | None = None,
    recurrence: TaskRecurrence = TaskRecurrence.NONE,
    assignee_id: int | None = None,
    assigned_group_id: int | None = None,
    prerequisite_ids: list[int] | None = None,
) -> Task:
    """
    Create a new task.

    Args:
        db: Database session
        scope: Authorization scope
        title: Task title
        description: Task description
        notes: Task notes
        task_status: Task status
        urgency: Task urgency
        due_date: Due date
        deferred_until: Deferred until date
        recurrence: Recurrence pattern
        assignee_id: Assigned user ID
        assigned_group_id: Assigned group ID
        prerequisite_ids: List of prerequisite task IDs

    Returns:
        Created task

    Raises:
        HTTPException: If validation fails
    """
    # Validate single assignment
    if assignee_id and assigned_group_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign to both user and group",
        )

    # Create task
    task = Task(
        user_id=scope.user.id,
        title=title,
        description=description,
        notes=notes,
        status=task_status.value if isinstance(task_status, TaskStatus) else task_status,
        urgency=urgency,
        due_date=due_date,
        deferred_until=deferred_until,
        recurrence=recurrence.value
        if isinstance(recurrence, TaskRecurrence)
        else recurrence,
        assignee_id=assignee_id,
        assigned_group_id=assigned_group_id,
    )
    db.add(task)
    db.flush()  # Get task ID without committing

    # Add prerequisites
    if prerequisite_ids:
        for prereq_id in prerequisite_ids:
            # Verify prerequisite exists and user has access
            prereq_task = get_task_by_id(db, scope, prereq_id)
            if not prereq_task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Prerequisite task {prereq_id} not found",
                )

            dependency = TaskDependency(
                blocked_task_id=task.id, prereq_task_id=prereq_id
            )
            db.add(dependency)

    db.commit()
    db.refresh(task)

    # Load relationships for response
    return _load_task_relationships(db, task)


def get_task_by_id(db: Session, scope: Scope, task_id: int) -> Task | None:
    """
    Get a task by ID if user has access.

    Args:
        db: Database session
        scope: Authorization scope
        task_id: Task ID

    Returns:
        Task if found and accessible, None otherwise
    """
    stmt = select(Task).where(Task.id == task_id)
    task = db.execute(stmt).scalar_one_or_none()

    if not task:
        return None

    if not can_access_task(db, scope, task):
        return None

    return _load_task_relationships(db, task)


def list_tasks(db: Session, scope: Scope, status_filter: str | None = None) -> list[Task]:
    """
    List all tasks visible to the user.

    Args:
        db: Database session
        scope: Authorization scope
        status_filter: Optional status filter

    Returns:
        List of tasks
    """
    tasks = get_tasks_for_scope(db, scope, status_filter)
    return [_load_task_relationships(db, task) for task in tasks]


def update_task(
    db: Session,
    scope: Scope,
    task_id: int,
    updates: dict[str, Any],
) -> Task:
    """
    Update a task.

    Args:
        db: Database session
        scope: Authorization scope
        task_id: Task ID
        updates: Dictionary of fields to update

    Returns:
        Updated task

    Raises:
        HTTPException: If task not found, unauthorized, or validation fails
    """
    task = get_task_by_id(db, scope, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if not can_modify_task(scope, task):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this task",
        )

    # Validate single assignment if both are being set
    if "assignee_id" in updates and "assigned_group_id" in updates:
        if updates["assignee_id"] and updates["assigned_group_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign to both user and group",
            )

    # Update prerequisite dependencies if provided
    prerequisite_ids = updates.pop("prerequisite_ids", None)
    if prerequisite_ids is not None:
        # Remove existing dependencies
        stmt = select(TaskDependency).where(TaskDependency.blocked_task_id == task.id)
        existing_deps = db.execute(stmt).scalars().all()
        for dep in existing_deps:
            db.delete(dep)

        # Add new dependencies
        for prereq_id in prerequisite_ids:
            prereq_task = get_task_by_id(db, scope, prereq_id)
            if not prereq_task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Prerequisite task {prereq_id} not found",
                )

            dependency = TaskDependency(
                blocked_task_id=task.id, prereq_task_id=prereq_id
            )
            db.add(dependency)

    # Update other fields
    for field, value in updates.items():
        if value is not None and hasattr(task, field):
            # Handle enum values
            if field in ["status", "urgency", "recurrence"]:
                if hasattr(value, "value"):
                    value = value.value
            setattr(task, field, value)

    task.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(task)

    return _load_task_relationships(db, task)


def delete_task(db: Session, scope: Scope, task_id: int) -> None:
    """
    Delete a task.

    Args:
        db: Database session
        scope: Authorization scope
        task_id: Task ID

    Raises:
        HTTPException: If task not found or unauthorized
    """
    task = get_task_by_id(db, scope, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if not can_modify_task(scope, task):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this task",
        )

    db.delete(task)
    db.commit()


def complete_task(db: Session, scope: Scope, task_id: int) -> Task:
    """
    Complete a task, validating all prerequisites are done.

    If the task has recurrence, create a new task with advanced due date.

    Args:
        db: Database session
        scope: Authorization scope
        task_id: Task ID

    Returns:
        The completed task (or the new recurring task if applicable)

    Raises:
        HTTPException: If task not found, unauthorized, or prerequisites incomplete
    """
    task = get_task_by_id(db, scope, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if not can_modify_task(scope, task):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to complete this task",
        )

    # Check all prerequisites are done
    stmt = (
        select(Task)
        .join(TaskDependency, TaskDependency.prereq_task_id == Task.id)
        .where(TaskDependency.blocked_task_id == task.id)
    )
    prerequisites = db.execute(stmt).scalars().all()

    incomplete_prereqs = [p for p in prerequisites if p.status != TaskStatus.DONE.value]
    if incomplete_prereqs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete: {len(incomplete_prereqs)} incomplete prerequisites",
        )

    # Mark task as done
    task.status = TaskStatus.DONE.value
    task.updated_at = datetime.now(UTC)
    db.commit()

    # Handle recurrence
    if task.recurrence != TaskRecurrence.NONE.value:
        new_task = _create_recurring_task(db, task)
        db.commit()
        return _load_task_relationships(db, new_task)

    return _load_task_relationships(db, task)


def _create_recurring_task(db: Session, original_task: Task) -> Task:
    """
    Create the next instance of a recurring task.

    Args:
        db: Database session
        original_task: Original completed task

    Returns:
        New recurring task
    """
    # Calculate new due date
    new_due_date = None
    if original_task.due_date:
        if original_task.recurrence == TaskRecurrence.DAILY.value:
            new_due_date = original_task.due_date + relativedelta(days=1)
        elif original_task.recurrence == TaskRecurrence.WEEKLY.value:
            new_due_date = original_task.due_date + relativedelta(weeks=1)
        elif original_task.recurrence == TaskRecurrence.MONTHLY.value:
            new_due_date = original_task.due_date + relativedelta(months=1)
        elif original_task.recurrence == TaskRecurrence.YEARLY.value:
            new_due_date = original_task.due_date + relativedelta(years=1)

    # Create new task
    new_task = Task(
        user_id=original_task.user_id,
        assignee_id=original_task.assignee_id,
        assigned_group_id=original_task.assigned_group_id,
        title=original_task.title,
        description=original_task.description,
        notes=original_task.notes,
        status=TaskStatus.TODO.value,
        urgency=original_task.urgency,
        due_date=new_due_date,
        recurrence=original_task.recurrence,
    )
    db.add(new_task)
    db.flush()

    # Copy prerequisite dependencies
    stmt = select(TaskDependency).where(
        TaskDependency.blocked_task_id == original_task.id
    )
    original_deps = db.execute(stmt).scalars().all()

    for dep in original_deps:
        new_dep = TaskDependency(
            blocked_task_id=new_task.id, prereq_task_id=dep.prereq_task_id
        )
        db.add(new_dep)

    return new_task


def _load_task_relationships(db: Session, task: Task) -> Task:
    """
    Load task relationships for complete response.

    Args:
        db: Database session
        task: Task to load relationships for

    Returns:
        Task with loaded relationships
    """
    # Refresh task to ensure we have latest data
    db.refresh(task)

    # Manually load prerequisites
    stmt = (
        select(Task)
        .join(TaskDependency, TaskDependency.prereq_task_id == Task.id)
        .where(TaskDependency.blocked_task_id == task.id)
    )
    prerequisites = db.execute(stmt).scalars().all()

    # Manually load dependents
    stmt = (
        select(Task)
        .join(TaskDependency, TaskDependency.blocked_task_id == Task.id)
        .where(TaskDependency.prereq_task_id == task.id)
    )
    dependents = db.execute(stmt).scalars().all()

    # Set attributes for serialization
    task.prerequisites = prerequisites  # type: ignore
    task.dependents = dependents  # type: ignore

    return task
