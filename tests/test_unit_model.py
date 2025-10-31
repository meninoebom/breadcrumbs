"""Tests for the Unit model."""
from datetime import datetime, timezone
import pytest
from sqlmodel import Session, select

from app.models import Unit, Crumb


def test_unit_create_minimal(session: Session):
    """Test creating a unit with minimal required fields."""
    unit = Unit(name="morning-thoughts")
    session.add(unit)
    session.commit()
    session.refresh(unit)

    assert unit.id is not None
    assert unit.name == "morning-thoughts"
    assert unit.created_at is not None
    assert isinstance(unit.created_at, datetime)


def test_unit_create_with_custom_created_at(session: Session):
    """Test creating a unit with a custom created_at timestamp."""
    custom_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    unit = Unit(name="afternoon-session", created_at=custom_time)
    session.add(unit)
    session.commit()
    session.refresh(unit)

    assert unit.id is not None
    assert unit.name == "afternoon-session"
    # SQLite doesn't preserve timezone info, so compare without it
    assert unit.created_at.replace(tzinfo=None) == custom_time.replace(tzinfo=None)


def test_unit_save_and_retrieve(session: Session):
    """Test saving a unit and retrieving it from the database."""
    # Create and save
    unit = Unit(name="test-session")
    session.add(unit)
    session.commit()
    unit_id = unit.id

    # Clear session to force database fetch
    session.expire_all()

    # Retrieve
    retrieved_unit = session.get(Unit, unit_id)

    assert retrieved_unit is not None
    assert retrieved_unit.id == unit_id
    assert retrieved_unit.name == "test-session"


def test_unit_with_crumbs(session: Session):
    """Test creating a unit with associated crumbs."""
    unit = Unit(name="writing-session")
    session.add(unit)
    session.commit()
    session.refresh(unit)

    # Create crumbs associated with this unit
    crumb1 = Crumb(body_md="First thought", unit_id=unit.id)
    crumb2 = Crumb(body_md="Second thought", unit_id=unit.id)
    crumb3 = Crumb(body_md="Third thought", unit_id=unit.id)

    session.add_all([crumb1, crumb2, crumb3])
    session.commit()
    session.refresh(unit)

    assert len(unit.crumbs) == 3
    crumb_bodies = {c.body_md for c in unit.crumbs}
    assert crumb_bodies == {"First thought", "Second thought", "Third thought"}


def test_unit_relationship_bidirectional(session: Session):
    """Test that the unit-crumb relationship works bidirectionally."""
    unit = Unit(name="test-unit")
    session.add(unit)
    session.commit()
    session.refresh(unit)

    crumb = Crumb(body_md="Test crumb", unit_id=unit.id)
    session.add(crumb)
    session.commit()
    session.refresh(crumb)
    session.refresh(unit)

    # Test forward relationship (unit -> crumbs)
    assert len(unit.crumbs) == 1
    assert unit.crumbs[0].body_md == "Test crumb"

    # Test backward relationship (crumb -> unit)
    assert crumb.unit is not None
    assert crumb.unit.name == "test-unit"


def test_unit_multiple_with_same_name(session: Session):
    """Test that multiple units can have the same name (different sessions)."""
    # Create two units with the same name but different timestamps
    unit1 = Unit(name="daily-thoughts")
    session.add(unit1)
    session.commit()
    session.refresh(unit1)

    unit2 = Unit(name="daily-thoughts")
    session.add(unit2)
    session.commit()
    session.refresh(unit2)

    # Both should exist with different IDs
    assert unit1.id != unit2.id
    assert unit1.name == unit2.name == "daily-thoughts"
    # created_at might be different due to different creation times
    assert unit1.created_at <= unit2.created_at


def test_unit_query_all(session: Session):
    """Test querying all units."""
    unit1 = Unit(name="session-1")
    unit2 = Unit(name="session-2")
    unit3 = Unit(name="session-3")
    session.add_all([unit1, unit2, unit3])
    session.commit()

    # Query all
    statement = select(Unit)
    results = session.exec(statement).all()

    assert len(results) == 3
    unit_names = {u.name for u in results}
    assert unit_names == {"session-1", "session-2", "session-3"}


def test_unit_query_by_name(session: Session):
    """Test querying units by name."""
    unit1 = Unit(name="morning-session")
    unit2 = Unit(name="afternoon-session")
    unit3 = Unit(name="morning-session")  # Duplicate name, different session
    session.add_all([unit1, unit2, unit3])
    session.commit()

    # Query by name
    statement = select(Unit).where(Unit.name == "morning-session")
    results = session.exec(statement).all()

    assert len(results) == 2
    for unit in results:
        assert unit.name == "morning-session"


def test_unit_str_representation(session: Session):
    """Test the string representation of a unit."""
    unit = Unit(name="test-session")
    session.add(unit)
    session.commit()
    session.refresh(unit)

    unit_str = str(unit)
    assert f"Unit(id={unit.id}" in unit_str
    assert "name=test-session" in unit_str
    assert "created_at=" in unit_str


def test_unit_empty_crumbs_list(session: Session):
    """Test that a unit without crumbs has an empty crumbs list."""
    unit = Unit(name="empty-session")
    session.add(unit)
    session.commit()
    session.refresh(unit)

    assert unit.crumbs == []
    assert len(unit.crumbs) == 0


def test_unit_name_max_length(session: Session):
    """Test that unit names can be up to 100 characters."""
    long_name = "a" * 100
    unit = Unit(name=long_name)
    session.add(unit)
    session.commit()
    session.refresh(unit)

    assert unit.name == long_name
    assert len(unit.name) == 100


def test_unit_order_by_created_at(session: Session):
    """Test ordering units by created_at timestamp."""
    # Create units with specific timestamps
    time1 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    time2 = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
    time3 = datetime(2024, 1, 3, 10, 0, 0, tzinfo=timezone.utc)

    unit1 = Unit(name="session-1", created_at=time2)
    unit2 = Unit(name="session-2", created_at=time1)
    unit3 = Unit(name="session-3", created_at=time3)

    session.add_all([unit1, unit2, unit3])
    session.commit()

    # Query ordered by created_at
    statement = select(Unit).order_by(Unit.created_at)
    results = session.exec(statement).all()

    assert len(results) == 3
    assert results[0].name == "session-2"  # Earliest
    assert results[1].name == "session-1"
    assert results[2].name == "session-3"  # Latest
