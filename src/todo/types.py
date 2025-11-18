"""Custom SQLAlchemy types for cross-database compatibility."""

from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import CITEXT as PostgresCITEXT


class CITEXT(TypeDecorator):
    """Case-insensitive text type that works across different databases.

    Uses PostgreSQL's CITEXT for PostgreSQL, and regular String for other databases
    like SQLite. This allows models to work in both production (PostgreSQL) and
    test (SQLite) environments.
    """

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Load the appropriate type implementation based on the database dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgresCITEXT())
        else:
            return dialect.type_descriptor(String())
