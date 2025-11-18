"""Token models for authentication."""
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserToken(Base):
    """Session token for web UI authentication."""

    __tablename__ = "users_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    context: Mapped[str] = mapped_column(String, nullable=False, default="session")
    authenticated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    inserted_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), default=lambda: datetime.now(UTC)
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="session_tokens")

    def __repr__(self) -> str:
        return f"<UserToken(id={self.id}, user_id={self.user_id}, context={self.context})>"


class UserAccessToken(Base):
    """API access token for Bearer authentication."""

    __tablename__ = "user_access_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary, unique=True, nullable=False, index=True)
    token_prefix: Mapped[str] = mapped_column(String, nullable=False)  # First 8 chars for display
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
    user: Mapped["User"] = relationship("User", back_populates="access_tokens")

    def __repr__(self) -> str:
        return f"<UserAccessToken(id={self.id}, user_id={self.user_id}, prefix={self.token_prefix})>"


class UserPreference(Base):
    """User preferences including custom LLM prompts."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    prompt_preferences: Mapped[str | None] = mapped_column(String(2000), nullable=True)
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
    user: Mapped["User"] = relationship("User", back_populates="preference")

    def __repr__(self) -> str:
        return f"<UserPreference(id={self.id}, user_id={self.user_id})>"
