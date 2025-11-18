"""User model."""
from datetime import UTC, datetime

from sqlalchemy import String, func
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from todo.database import Base


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    inserted_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    session_tokens: Mapped[list["UserToken"]] = relationship(
        "UserToken", back_populates="user", cascade="all, delete-orphan"
    )
    access_tokens: Mapped[list["UserAccessToken"]] = relationship(
        "UserAccessToken", back_populates="user", cascade="all, delete-orphan"
    )
    preference: Mapped["UserPreference | None"] = relationship(
        "UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    created_groups: Mapped[list["Group"]] = relationship(
        "Group", back_populates="created_by", cascade="all, delete-orphan"
    )
    group_memberships: Mapped[list["GroupMembership"]] = relationship(
        "GroupMembership",
        foreign_keys="[GroupMembership.user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    owned_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        foreign_keys="[Task.user_id]",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    assigned_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        foreign_keys="[Task.assignee_id]",
        back_populates="assignee",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
