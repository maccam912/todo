"""Task Pydantic schemas."""
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.task import TaskRecurrence, TaskStatus, TaskUrgency


class TaskDependencyResponse(BaseModel):
    """Schema for task dependency in responses."""

    id: int
    title: str
    status: TaskStatus

    model_config = {"from_attributes": True}


class TaskBase(BaseModel):
    """Base task schema."""

    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str | None = Field(None, max_length=10000, description="Task description")
    notes: str | None = Field(None, max_length=10000, description="Task notes")
    status: TaskStatus = Field(default=TaskStatus.TODO, description="Task status")
    urgency: TaskUrgency = Field(default=TaskUrgency.NORMAL, description="Task urgency")
    due_date: date | None = Field(None, description="Due date")
    deferred_until: date | None = Field(None, description="Deferred until date")
    recurrence: TaskRecurrence = Field(
        default=TaskRecurrence.NONE, description="Recurrence pattern"
    )


class TaskCreate(TaskBase):
    """Schema for creating a task."""

    assignee_id: int | None = Field(None, description="Assigned user ID")
    assigned_group_id: int | None = Field(None, description="Assigned group ID")
    prerequisite_ids: list[int] = Field(default=[], description="List of prerequisite task IDs")

    @field_validator("assignee_id", "assigned_group_id")
    @classmethod
    def validate_single_assignment(cls, v, info):
        """Validate that only one assignment type is set."""
        if info.field_name == "assigned_group_id" and v is not None:
            if info.data.get("assignee_id") is not None:
                raise ValueError("Cannot assign to both user and group")
        return v


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=10000)
    notes: str | None = Field(None, max_length=10000)
    status: TaskStatus | None = None
    urgency: TaskUrgency | None = None
    due_date: date | None = None
    deferred_until: date | None = None
    recurrence: TaskRecurrence | None = None
    assignee_id: int | None = None
    assigned_group_id: int | None = None
    prerequisite_ids: list[int] | None = None

    @field_validator("assignee_id", "assigned_group_id")
    @classmethod
    def validate_single_assignment(cls, v, info):
        """Validate that only one assignment type is set."""
        if info.field_name == "assigned_group_id" and v is not None:
            if info.data.get("assignee_id") is not None:
                raise ValueError("Cannot assign to both user and group")
        return v


class TaskResponse(TaskBase):
    """Schema for task response."""

    id: int
    user_id: int
    assignee_id: int | None
    assigned_group_id: int | None
    prerequisites: list[TaskDependencyResponse] = []
    dependents: list[TaskDependencyResponse] = []
    inserted_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """Schema for task list response."""

    data: list[TaskResponse]


class TaskProcessRequest(BaseModel):
    """Schema for natural language task processing request."""

    text: str = Field(..., min_length=1, description="Natural language request")


class TaskCommandResponse(BaseModel):
    """Schema for a single command executed by the state machine."""

    command: str
    target: str | None = None
    attributes: dict | None = None
    result: str


class TaskProcessResponse(BaseModel):
    """Schema for natural language task processing response."""

    actions: list[TaskCommandResponse]
    message: str
    session_id: str
