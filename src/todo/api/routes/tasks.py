"""Task routes."""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from todo.api.deps import AppSettings, CurrentScopeWithPrefs, DatabaseSession
from todo.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskProcessRequest,
    TaskProcessResponse,
    TaskResponse,
    TaskUpdate,
)
from todo.services.conversation_service import ConversationService
from todo.services.task_service import (
    complete_task,
    create_task,
    delete_task,
    get_task_by_id,
    list_tasks,
    update_task,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse)
def list_all_tasks(
    scope: CurrentScopeWithPrefs,
    db: DatabaseSession,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
):
    """
    List all tasks visible to the current user.

    Args:
        scope: Current user scope
        db: Database session
        status: Optional status filter

    Returns:
        List of tasks
    """
    tasks = list_tasks(db, scope, status)
    return TaskListResponse(data=tasks)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_new_task(
    task_data: TaskCreate,
    scope: CurrentScopeWithPrefs,
    db: DatabaseSession,
):
    """
    Create a new task.

    Args:
        task_data: Task creation data
        scope: Current user scope
        db: Database session

    Returns:
        Created task
    """
    task = create_task(
        db,
        scope,
        title=task_data.title,
        description=task_data.description,
        notes=task_data.notes,
        task_status=task_data.status,
        urgency=task_data.urgency.value,
        due_date=task_data.due_date,
        deferred_until=task_data.deferred_until,
        recurrence=task_data.recurrence,
        assignee_id=task_data.assignee_id,
        assigned_group_id=task_data.assigned_group_id,
        prerequisite_ids=task_data.prerequisite_ids,
    )
    return task


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    scope: CurrentScopeWithPrefs,
    db: DatabaseSession,
):
    """
    Get a specific task.

    Args:
        task_id: Task ID
        scope: Current user scope
        db: Database session

    Returns:
        Task

    Raises:
        HTTPException: If task not found
    """
    task = get_task_by_id(db, scope, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
@router.put("/{task_id}", response_model=TaskResponse)
def update_existing_task(
    task_id: int,
    task_data: TaskUpdate,
    scope: CurrentScopeWithPrefs,
    db: DatabaseSession,
):
    """
    Update a task.

    Args:
        task_id: Task ID
        task_data: Task update data
        scope: Current user scope
        db: Database session

    Returns:
        Updated task
    """
    # Convert Pydantic model to dict, excluding None values
    updates = task_data.model_dump(exclude_none=True)
    task = update_task(db, scope, task_id, updates)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_task(
    task_id: int,
    scope: CurrentScopeWithPrefs,
    db: DatabaseSession,
):
    """
    Delete a task.

    Args:
        task_id: Task ID
        scope: Current user scope
        db: Database session
    """
    delete_task(db, scope, task_id)


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_existing_task(
    task_id: int,
    scope: CurrentScopeWithPrefs,
    db: DatabaseSession,
):
    """
    Complete a task.

    Args:
        task_id: Task ID
        scope: Current user scope
        db: Database session

    Returns:
        Completed task (or new recurring task if applicable)
    """
    task = complete_task(db, scope, task_id)
    return task


@router.post("/process", response_model=TaskProcessResponse)
async def process_natural_language(
    request: TaskProcessRequest,
    scope: CurrentScopeWithPrefs,
    db: DatabaseSession,
    settings: AppSettings,
):
    """
    Process a natural language request to manage tasks.

    Args:
        request: Natural language request
        scope: Current user scope with preferences
        db: Database session
        settings: Application settings

    Returns:
        Processing result with executed actions
    """
    conversation_service = ConversationService(settings)

    try:
        actions, message, session_id = await conversation_service.process_request(
            db, scope, request.text
        )

        return TaskProcessResponse(
            actions=actions,
            message=message,
            session_id=session_id,
        )

    finally:
        await conversation_service.close()
