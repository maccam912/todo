"""Database setup and session management."""

from collections.abc import Generator
from typing import Any

from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from todo.config import Settings, get_settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Global engine and session factory
engine: Any = None
SessionLocal: Any = None


def init_db(settings: Settings | None = None) -> None:
    """Initialize database engine and session factory."""
    global engine, SessionLocal

    if settings is None:
        settings = get_settings()

    # Create engine
    engine = create_engine(
        str(settings.database_url),
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        echo=settings.db_echo,
    )

    # Instrument SQLAlchemy with OpenTelemetry
    if settings.otel_enabled:
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            service=settings.otel_service_name,
        )

    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session]:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
