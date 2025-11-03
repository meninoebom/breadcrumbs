"""Database configuration and session management."""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///breadcrumbs.sqlite")

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
