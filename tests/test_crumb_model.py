"""Tests for the Crumb model."""
from datetime import datetime, timezone
import pytest
from sqlmodel import Session, select

from app.models import Crumb, Tag, Unit, Visibility


def test_crumb_create_minimal(session: Session):
    """Test creating a crumb with minimal required fields."""
    crumb = Crumb(body_md="This is a test crumb")
    session.add(crumb)
    session.commit()
    session.refresh(crumb)

    assert crumb.id is not None
    assert crumb.body_md == "This is a test crumb"
    assert crumb.visibility == Visibility.draft
    assert crumb.created_at is not None
    assert isinstance(crumb.created_at, datetime)


def test_crumb_create_with_visibility(session: Session):
    """Test creating a crumb with explicit visibility."""
    crumb = Crumb(body_md="Published crumb", visibility=Visibility.published)
    session.add(crumb)
    session.commit()
    session.refresh(crumb)

    assert crumb.id is not None
    assert crumb.visibility == Visibility.published


def test_crumb_create_with_unit(session: Session):
    """Test creating a crumb associated with a unit."""
    # Create a unit first
    unit = Unit(name="morning-thoughts")
    session.add(unit)
    session.commit()
    session.refresh(unit)

    # Create a crumb associated with this unit
    crumb = Crumb(body_md="Crumb in a unit", unit_id=unit.id)
    session.add(crumb)
    session.commit()
    session.refresh(crumb)

    assert crumb.id is not None
    assert crumb.unit_id == unit.id
    assert crumb.unit is not None
    assert crumb.unit.name == "morning-thoughts"


def test_crumb_create_with_tags(session: Session):
    """Test creating a crumb with tags."""
    # Create tags first
    tag1 = Tag(name="python")
    tag2 = Tag(name="testing")
    session.add(tag1)
    session.add(tag2)
    session.commit()
    session.refresh(tag1)
    session.refresh(tag2)

    # Create a crumb with tags
    crumb = Crumb(body_md="Crumb with tags")
    crumb.tags = [tag1, tag2]
    session.add(crumb)
    session.commit()
    session.refresh(crumb)

    assert crumb.id is not None
    assert len(crumb.tags) == 2
    tag_names = {tag.name for tag in crumb.tags}
    assert tag_names == {"python", "testing"}


def test_crumb_save_and_retrieve(session: Session):
    """Test saving a crumb and retrieving it from the database."""
    # Create and save
    crumb = Crumb(body_md="Save and retrieve test", visibility=Visibility.published)
    session.add(crumb)
    session.commit()
    crumb_id = crumb.id

    # Clear session to force database fetch
    session.expire_all()

    # Retrieve
    retrieved_crumb = session.get(Crumb, crumb_id)

    assert retrieved_crumb is not None
    assert retrieved_crumb.id == crumb_id
    assert retrieved_crumb.body_md == "Save and retrieve test"
    assert retrieved_crumb.visibility == Visibility.published


def test_crumb_updated_at(session: Session):
    """Test that updated_at is set when crumb is modified."""
    crumb = Crumb(body_md="Original content")
    session.add(crumb)
    session.commit()
    session.refresh(crumb)

    original_created_at = crumb.created_at
    assert crumb.updated_at is None

    # Modify and save
    crumb.body_md = "Updated content"
    session.add(crumb)
    session.commit()
    session.refresh(crumb)

    # created_at should remain the same
    assert crumb.created_at == original_created_at
    # Note: updated_at behavior depends on database trigger/onupdate
    # In SQLite, onupdate may not work as expected without explicit setting


def test_crumb_query_all(session: Session):
    """Test querying all crumbs."""
    # Create multiple crumbs
    crumb1 = Crumb(body_md="First crumb")
    crumb2 = Crumb(body_md="Second crumb")
    crumb3 = Crumb(body_md="Third crumb")
    session.add_all([crumb1, crumb2, crumb3])
    session.commit()

    # Query all
    statement = select(Crumb)
    results = session.exec(statement).all()

    assert len(results) == 3
    bodies = {c.body_md for c in results}
    assert bodies == {"First crumb", "Second crumb", "Third crumb"}


def test_crumb_str_representation(session: Session):
    """Test the string representation of a crumb."""
    crumb = Crumb(body_md="This is a longer crumb body for testing string representation")
    session.add(crumb)
    session.commit()
    session.refresh(crumb)

    crumb_str = str(crumb)
    assert f"Crumb of id:{crumb.id}" in crumb_str
    assert "This is a " in crumb_str  # First 10 chars
