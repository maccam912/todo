"""Task models."""

from datetime import UTC, date, datetime
from enum import Enum

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from todo.database import Base


class TaskStatus(str, Enum):
    """Task status enum."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskUrgency(str, Enum):
    """Task urgency enum."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskRecurrence(str, Enum):
    """Task recurrence enum."""

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class Task(Base):
    """Task model."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(10000), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(10000), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TaskStatus.TODO.value, index=True
    )
    urgency: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TaskUrgency.NORMAL.value
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    deferred_until: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    recurrence: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TaskRecurrence.NONE.value
    )
    inserted_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Constraints
    __table_args__ = (
        # Cannot be assigned to both user AND group
        CheckConstraint(
            "NOT (assignee_id IS NOT NULL AND assigned_group_id IS NOT NULL)",
            name="check_single_assignment",
        ),
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="owned_tasks",
    )
    assignee: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assignee_id],
        back_populates="assigned_tasks",
    )
    assigned_group: Mapped["Group | None"] = relationship("Group", back_populates="assigned_tasks")

    # Dependencies - tasks that this task blocks (this task is a prerequisite for them)
    blocks: Mapped[list["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="[TaskDependency.prereq_task_id]",
        back_populates="prerequisite",
        cascade="all, delete-orphan",
    )

    # Dependencies - tasks that block this task (this task depends on them)
    blocked_by: Mapped[list["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="[TaskDependency.blocked_task_id]",
        back_populates="blocked_task",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title[:30]}, status={self.status})>"


class TaskDependency(Base):
    """Task dependency relationship."""

    __tablename__ = "task_dependencies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    blocked_task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prereq_task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inserted_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Constraints
    __table_args__ = (
        # Cannot depend on itself
        CheckConstraint(
            "blocked_task_id != prereq_task_id",
            name="no_self_reference",
        ),
        # Unique constraint
        UniqueConstraint(
            "blocked_task_id",
            "prereq_task_id",
            name="idx_task_dependencies_unique",
        ),
    )

    # Relationships
    blocked_task: Mapped["Task"] = relationship(
        "Task",
        foreign_keys=[blocked_task_id],
        back_populates="blocked_by",
    )
    prerequisite: Mapped["Task"] = relationship(
        "Task",
        foreign_keys=[prereq_task_id],
        back_populates="blocks",
    )

    def __repr__(self) -> str:
        return f"<TaskDependency(blocked={self.blocked_task_id}, prereq={self.prereq_task_id})>"
