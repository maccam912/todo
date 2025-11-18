"""Group models for task assignment."""
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from todo.database import Base


class Group(Base):
    """Group model for organizing users and nested groups."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
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

    # Relationships
    created_by: Mapped["User"] = relationship("User", back_populates="created_groups")
    memberships: Mapped[list["GroupMembership"]] = relationship(
        "GroupMembership",
        foreign_keys="[GroupMembership.group_id]",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    parent_memberships: Mapped[list["GroupMembership"]] = relationship(
        "GroupMembership",
        foreign_keys="[GroupMembership.member_group_id]",
        back_populates="member_group",
        cascade="all, delete-orphan",
    )
    assigned_tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="assigned_group"
    )

    def __repr__(self) -> str:
        return f"<Group(id={self.id}, name={self.name})>"


class GroupMembership(Base):
    """Group membership - supports both user and nested group members."""

    __tablename__ = "group_memberships"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    member_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True
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
        # Exactly one of user_id or member_group_id must be set
        CheckConstraint(
            "(user_id IS NOT NULL AND member_group_id IS NULL) OR "
            "(user_id IS NULL AND member_group_id IS NOT NULL)",
            name="exactly_one_member_type",
        ),
        # Unique constraint for user members
        UniqueConstraint(
            "group_id",
            "user_id",
            name="idx_group_memberships_group_user",
        ),
        # Unique constraint for group members
        UniqueConstraint(
            "group_id",
            "member_group_id",
            name="idx_group_memberships_group_group",
        ),
    )

    # Relationships
    group: Mapped["Group"] = relationship(
        "Group",
        foreign_keys=[group_id],
        back_populates="memberships",
    )
    user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="group_memberships",
    )
    member_group: Mapped["Group | None"] = relationship(
        "Group",
        foreign_keys=[member_group_id],
        back_populates="parent_memberships",
    )

    def __repr__(self) -> str:
        member_type = f"user_id={self.user_id}" if self.user_id else f"group_id={self.member_group_id}"
        return f"<GroupMembership(id={self.id}, group_id={self.group_id}, {member_type})>"
