"""Database configuration and session management."""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key enforcement for SQLite connections only."""
    import sqlite3

    if not isinstance(dbapi_connection, sqlite3.Connection):
        return

    ac = dbapi_connection.autocommit
    dbapi_connection.autocommit = True

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

    dbapi_connection.autocommit = ac

load_dotenv()


def normalize_database_url(url: str) -> str:
    """Convert postgresql:// to postgresql+psycopg:// for psycopg3 compatibility.

    Railway provides postgresql:// URLs, but SQLAlchemy needs the +psycopg
    driver suffix to use psycopg3.
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


# Database URL from environment
DATABASE_URL = normalize_database_url(
    os.getenv("DATABASE_URL", "sqlite:///breadcrumbs.sqlite")
)

# Echo SQL in development
ECHO_SQL = os.getenv("ENVIRONMENT", "development") == "development"

# Create engine with appropriate settings
engine = create_engine(
    DATABASE_URL,
    echo=ECHO_SQL,
    # Postgres-specific: connection pool settings (ignored by SQLite)
    pool_pre_ping=True,  # Verify connections before using to avoid errors
    pool_size=5,  # Number of connections to keep
    max_overflow=10,  # Extra connections if needed
)


def get_session() -> Generator[Session, None, None]:
    """Database session dependency for FastAPI routes."""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            # If you don’t roll it back, the session stays in a bad state
            # and very further query will fail with: `sqlalchemy.exc.PendingRollbackError`
            session.rollback()
            raise
