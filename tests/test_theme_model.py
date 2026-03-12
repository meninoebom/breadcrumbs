"""Tests for the Theme model."""

from datetime import datetime, timezone
import pytest
from sqlmodel import Session, select
from pydantic import ValidationError

from app.models import Theme, Breadcrumb, Tag, Visibility


def test_theme_create_minimal(session: Session):
    """Test creating a theme with minimal required fields."""
    theme = Theme(body_md="A thought about something")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    assert theme.id is not None
    assert theme.body_md == "A thought about something"
    assert theme.visibility == Visibility.draft  # Default
    assert theme.created_at is not None
    assert isinstance(theme.created_at, datetime)


def test_theme_requires_body(session: Session):
    """Test that theme requires body_md."""
    with pytest.raises(ValidationError, match="Field required"):
        Theme.model_validate({})  # Missing required body_md field


def test_theme_visibility_published(session: Session):
    """Test creating a published theme."""
    theme = Theme(body_md="Published thought", visibility=Visibility.published)
    session.add(theme)
    session.commit()
    session.refresh(theme)

    assert theme.visibility == Visibility.published


def test_theme_save_and_retrieve(session: Session):
    """Test saving a theme and retrieving it from the database."""
    theme = Theme(body_md="Test thought")
    session.add(theme)
    session.commit()
    theme_id = theme.id

    session.expire_all()

    retrieved_theme = session.get(Theme, theme_id)

    assert retrieved_theme is not None
    assert retrieved_theme.id == theme_id
    assert retrieved_theme.body_md == "Test thought"


def test_theme_with_breadcrumbs(session: Session):
    """Test creating a theme with associated breadcrumbs."""
    theme = Theme(body_md="Main thought")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    crumb1 = Breadcrumb(body_md="Follow-up one", theme_id=theme.id)
    crumb2 = Breadcrumb(body_md="Follow-up two", theme_id=theme.id)
    crumb3 = Breadcrumb(body_md="Follow-up three", theme_id=theme.id)

    session.add_all([crumb1, crumb2, crumb3])
    session.commit()
    session.refresh(theme)

    assert len(theme.breadcrumbs) == 3
    breadcrumb_bodies = {c.body_md for c in theme.breadcrumbs}
    assert breadcrumb_bodies == {"Follow-up one", "Follow-up two", "Follow-up three"}


def test_theme_relationship_bidirectional(session: Session):
    """Test that the theme-breadcrumb relationship works bidirectionally."""
    theme = Theme(body_md="Main thought")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    breadcrumb = Breadcrumb(body_md="Sub-thought", theme_id=theme.id)
    session.add(breadcrumb)
    session.commit()
    session.refresh(breadcrumb)
    session.refresh(theme)

    assert len(theme.breadcrumbs) == 1
    assert theme.breadcrumbs[0].body_md == "Sub-thought"

    assert breadcrumb.theme is not None
    assert breadcrumb.theme.body_md == "Main thought"


def test_theme_with_tags(session: Session):
    """Test theme with tags relationship."""
    theme = Theme(body_md="Tagged thought")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    tag1 = Tag(name="python")
    tag2 = Tag(name="testing")
    session.add_all([tag1, tag2])
    session.commit()
    session.refresh(tag1)
    session.refresh(tag2)

    theme.tags = [tag1, tag2]
    session.add(theme)
    session.commit()
    session.refresh(theme)

    assert len(theme.tags) == 2
    tag_names = {tag.name for tag in theme.tags}
    assert tag_names == {"python", "testing"}


def test_theme_query_all(session: Session):
    """Test querying all themes."""
    theme1 = Theme(body_md="Thought 1")
    theme2 = Theme(body_md="Thought 2")
    theme3 = Theme(body_md="Thought 3")
    session.add_all([theme1, theme2, theme3])
    session.commit()

    statement = select(Theme)
    results = session.exec(statement).all()

    assert len(results) == 3


def test_theme_query_by_visibility(session: Session):
    """Test querying themes by visibility."""
    theme1 = Theme(body_md="Draft 1", visibility=Visibility.draft)
    theme2 = Theme(body_md="Published one", visibility=Visibility.published)
    theme3 = Theme(body_md="Draft 2", visibility=Visibility.draft)
    session.add_all([theme1, theme2, theme3])
    session.commit()

    statement = select(Theme).where(Theme.visibility == Visibility.published)
    results = session.exec(statement).all()

    assert len(results) == 1
    assert results[0].body_md == "Published one"

    statement = select(Theme).where(Theme.visibility == Visibility.draft)
    results = session.exec(statement).all()

    assert len(results) == 2


def test_theme_str_representation(session: Session):
    """Test the string representation of a theme."""
    theme = Theme(body_md="Test thought", visibility=Visibility.published)
    session.add(theme)
    session.commit()
    session.refresh(theme)

    theme_str = str(theme)
    assert f"Theme(id={theme.id}" in theme_str
    assert "Test thought" in theme_str
    assert "visibility=Visibility.published" in theme_str


def test_theme_empty_breadcrumbs_list(session: Session):
    """Test that a theme without breadcrumbs has an empty breadcrumbs list."""
    theme = Theme(body_md="Standalone thought")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    assert theme.breadcrumbs == []
    assert len(theme.breadcrumbs) == 0


def test_theme_order_by_created_at(session: Session):
    """Test ordering themes by created_at timestamp."""
    time1 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    time2 = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
    time3 = datetime(2024, 1, 3, 10, 0, 0, tzinfo=timezone.utc)

    theme1 = Theme(body_md="Thought 1", created_at=time2)
    theme2 = Theme(body_md="Thought 2", created_at=time1)
    theme3 = Theme(body_md="Thought 3", created_at=time3)

    session.add_all([theme1, theme2, theme3])
    session.commit()

    statement = select(Theme).order_by(Theme.created_at)
    results = session.exec(statement).all()

    assert len(results) == 3
    assert results[0].body_md == "Thought 2"  # Earliest
    assert results[1].body_md == "Thought 1"
    assert results[2].body_md == "Thought 3"  # Latest


def test_theme_multiple_breadcrumbs_different_times(session: Session):
    """Test that breadcrumbs within a theme can have different timestamps."""
    theme = Theme(body_md="Time-based thought")
    session.add(theme)
    session.commit()
    session.refresh(theme)

    time1 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    time2 = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc)

    breadcrumb1 = Breadcrumb(body_md="First", theme_id=theme.id, created_at=time1)
    breadcrumb2 = Breadcrumb(body_md="Second", theme_id=theme.id, created_at=time2)

    session.add_all([breadcrumb1, breadcrumb2])
    session.commit()
    session.refresh(theme)

    assert len(theme.breadcrumbs) == 2
    assert theme.breadcrumbs[0].created_at != theme.breadcrumbs[1].created_at
