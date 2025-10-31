"""Pytest configuration and fixtures for breadcrumbs tests."""
import os
import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

# Import models to ensure they're registered before creating tables
from app.models import Crumb, Tag, Unit, CrumbTag


@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh in-memory SQLite database for each test."""
    # Use in-memory SQLite database for tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    SQLModel.metadata.create_all(engine)

    # Create session
    with Session(engine) as session:
        yield session
        # Rollback any uncommitted changes
        session.rollback()

    # Clean up
    SQLModel.metadata.drop_all(engine)
