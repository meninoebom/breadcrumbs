"""Tests for the Breadcrumb model."""

from datetime import datetime, timezone
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models import Breadcrumb, Theme


def test_breadcrumb_create_with_theme(session: Session):
    """Test creating a breadcrumb with a theme (required)."""
    # Create theme first
    theme = Theme(body_md="Test Theme")
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
    theme = Theme(body_md="Morning Thoughts")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    breadcrumb = Breadcrumb(body_md="Test thought", theme_id=theme.id)
    session.add(breadcrumb)
    session.commit()
    session.refresh(breadcrumb)

    assert breadcrumb.theme is not None
    assert breadcrumb.theme.body_md == "Morning Thoughts"


def test_breadcrumb_save_and_retrieve(session: Session):
    """Test saving a breadcrumb and retrieving it from the database."""
    # Create theme and breadcrumb
    theme = Theme(body_md="Test Theme")
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
    theme = Theme(body_md="Test Theme")
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
    theme = Theme(body_md="Test Theme")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    breadcrumb = Breadcrumb(
        body_md="This is a longer breadcrumb body for testing string representation",
        theme_id=theme.id,
    )
    session.add(breadcrumb)
    session.commit()
    session.refresh(breadcrumb)

    breadcrumb_str = str(breadcrumb)
    assert f"Breadcrumb of id:{breadcrumb.id}" in breadcrumb_str
    assert "This is a " in breadcrumb_str  # First 10 chars


def test_breadcrumb_order_by_created_at(session: Session):
    """Test ordering breadcrumbs by created_at timestamp."""
    theme = Theme(body_md="Test Theme")
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
    theme1 = Theme(body_md="Theme 1")
    theme2 = Theme(body_md="Theme 2")
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

    assert breadcrumb1.theme.body_md == "Theme 1"
    assert breadcrumb2.theme.body_md == "Theme 2"


# ---------- parent-child relationship ----------


def test_breadcrumb_no_parent_by_default(session: Session):
    """New breadcrumbs have parent_id=None by default."""
    theme = Theme(body_md="Test Theme")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    bc = Breadcrumb(body_md="Top-level thought", theme_id=theme.id)
    session.add(bc)
    session.commit()
    session.refresh(bc)

    assert bc.parent_id is None


def test_breadcrumb_with_parent(session: Session):
    """A breadcrumb can reference another breadcrumb as its parent."""
    theme = Theme(body_md="Test Theme")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    parent = Breadcrumb(body_md="Parent thought", theme_id=theme.id)
    session.add(parent)
    session.commit()
    session.refresh(parent)

    child = Breadcrumb(body_md="Child thought", theme_id=theme.id, parent_id=parent.id)
    session.add(child)
    session.commit()
    session.refresh(child)

    assert child.parent_id == parent.id


def test_breadcrumb_parent_cascade_delete(session: Session):
    """Deleting a parent breadcrumb cascades to its children."""
    theme = Theme(body_md="Test Theme")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    parent = Breadcrumb(body_md="Parent", theme_id=theme.id)
    session.add(parent)
    session.commit()
    session.refresh(parent)

    child = Breadcrumb(body_md="Child", theme_id=theme.id, parent_id=parent.id)
    session.add(child)
    session.commit()
    child_id = child.id

    # Delete parent
    session.delete(parent)
    session.commit()

    # Child should be gone
    assert session.get(Breadcrumb, child_id) is None


def test_breadcrumb_deep_chain(session: Session):
    """Breadcrumbs can form chains of arbitrary depth."""
    theme = Theme(body_md="Test Theme")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    # Create a chain: root -> level1 -> level2 -> level3
    root = Breadcrumb(body_md="Root", theme_id=theme.id)
    session.add(root)
    session.commit()
    session.refresh(root)

    level1 = Breadcrumb(body_md="Level 1", theme_id=theme.id, parent_id=root.id)
    session.add(level1)
    session.commit()
    session.refresh(level1)

    level2 = Breadcrumb(body_md="Level 2", theme_id=theme.id, parent_id=level1.id)
    session.add(level2)
    session.commit()
    session.refresh(level2)

    level3 = Breadcrumb(body_md="Level 3", theme_id=theme.id, parent_id=level2.id)
    session.add(level3)
    session.commit()
    session.refresh(level3)

    assert level1.parent_id == root.id
    assert level2.parent_id == level1.id
    assert level3.parent_id == level2.id

    # Deleting root should cascade to all descendants
    session.delete(root)
    session.commit()

    remaining = session.exec(select(Breadcrumb)).all()
    assert len(remaining) == 0
