"""Tests for the Breadcrumb model."""
from datetime import datetime, timezone
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models import Breadcrumb, Theme, Visibility


def test_breadcrumb_create_with_theme(session: Session):
    """Test creating a breadcrumb with a theme (required)."""
    # Create theme first
    theme = Theme(title="Test Theme")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    # Create breadcrumb
    breadcrumb = Breadcrumb(body_md="This is a test breadcrumb", theme_id=theme.id)
    session.add(breadcrumb)
    session.commit()
    session.refresh(breadcrumb)

    assert breadcrumb.id is not None
    assert breadcrumb.body_md == "This is a test breadcrumb"
    assert breadcrumb.theme_id == theme.id
    assert breadcrumb.created_at is not None
    assert isinstance(breadcrumb.created_at, datetime)


def test_breadcrumb_requires_theme(session: Session):
    """Test that breadcrumb requires a theme_id."""
    # Create breadcrumb without theme
    breadcrumb = Breadcrumb(body_md="Orphan breadcrumb")
    session.add(breadcrumb)

    # Should fail - theme_id is required
    with pytest.raises(IntegrityError):
        session.commit()


def test_breadcrumb_relationship_to_theme(session: Session):
    """Test breadcrumb -> theme relationship."""
    theme = Theme(title="Morning Thoughts")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    breadcrumb = Breadcrumb(body_md="Test thought", theme_id=theme.id)
    session.add(breadcrumb)
    session.commit()
    session.refresh(breadcrumb)

    assert breadcrumb.theme is not None
    assert breadcrumb.theme.title == "Morning Thoughts"


def test_breadcrumb_save_and_retrieve(session: Session):
    """Test saving a breadcrumb and retrieving it from the database."""
    # Create theme and breadcrumb
    theme = Theme(title="Test Theme")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    breadcrumb = Breadcrumb(body_md="Save and retrieve test", theme_id=theme.id)
    session.add(breadcrumb)
    session.commit()
    breadcrumb_id = breadcrumb.id

    # Clear session to force database fetch
    session.expire_all()

    # Retrieve
    retrieved_breadcrumb = session.get(Breadcrumb, breadcrumb_id)

    assert retrieved_breadcrumb is not None
    assert retrieved_breadcrumb.id == breadcrumb_id
    assert retrieved_breadcrumb.body_md == "Save and retrieve test"


def test_breadcrumb_query_all(session: Session):
    """Test querying all breadcrumbs."""
    theme = Theme(title="Test Theme")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    # Create multiple breadcrumbs
    breadcrumb1 = Breadcrumb(body_md="First breadcrumb", theme_id=theme.id)
    breadcrumb2 = Breadcrumb(body_md="Second breadcrumb", theme_id=theme.id)
    breadcrumb3 = Breadcrumb(body_md="Third breadcrumb", theme_id=theme.id)
    session.add_all([breadcrumb1, breadcrumb2, breadcrumb3])
    session.commit()

    # Query all
    statement = select(Breadcrumb)
    results = session.exec(statement).all()

    assert len(results) == 3
    bodies = {c.body_md for c in results}
    assert bodies == {"First breadcrumb", "Second breadcrumb", "Third breadcrumb"}


def test_breadcrumb_str_representation(session: Session):
    """Test the string representation of a breadcrumb."""
    theme = Theme(title="Test Theme")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    breadcrumb = Breadcrumb(
        body_md="This is a longer breadcrumb body for testing string representation",
        theme_id=theme.id
    )
    session.add(breadcrumb)
    session.commit()
    session.refresh(breadcrumb)

    breadcrumb_str = str(breadcrumb)
    assert f"Breadcrumb of id:{breadcrumb.id}" in breadcrumb_str
    assert "This is a " in breadcrumb_str  # First 10 chars


def test_breadcrumb_order_by_created_at(session: Session):
    """Test ordering breadcrumbs by created_at timestamp."""
    theme = Theme(title="Test Theme")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    # Create breadcrumbs with specific timestamps
    time1 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    time2 = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
    time3 = datetime(2024, 1, 3, 10, 0, 0, tzinfo=timezone.utc)

    breadcrumb1 = Breadcrumb(body_md="First", theme_id=theme.id, created_at=time2)
    breadcrumb2 = Breadcrumb(body_md="Second", theme_id=theme.id, created_at=time1)
    breadcrumb3 = Breadcrumb(body_md="Third", theme_id=theme.id, created_at=time3)

    session.add_all([breadcrumb1, breadcrumb2, breadcrumb3])
    session.commit()

    # Query ordered by created_at
    statement = select(Breadcrumb).order_by(Breadcrumb.created_at)
    results = session.exec(statement).all()

    assert len(results) == 3
    assert results[0].body_md == "Second"  # Earliest
    assert results[1].body_md == "First"
    assert results[2].body_md == "Third"  # Latest


def test_breadcrumb_multiple_themes(session: Session):
    """Test that breadcrumbs can belong to different themes."""
    theme1 = Theme(title="Theme 1")
    theme2 = Theme(title="Theme 2")
    session.add_all([theme1, theme2])
    session.commit()
    session.refresh(theme1)
    session.refresh(theme2)

    breadcrumb1 = Breadcrumb(body_md="Breadcrumb in theme 1", theme_id=theme1.id)
    breadcrumb2 = Breadcrumb(body_md="Breadcrumb in theme 2", theme_id=theme2.id)
    session.add_all([breadcrumb1, breadcrumb2])
    session.commit()
    session.refresh(breadcrumb1)
    session.refresh(breadcrumb2)

    assert breadcrumb1.theme.title == "Theme 1"
    assert breadcrumb2.theme.title == "Theme 2"
