from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
import re

from pydantic import field_validator
from sqlmodel import Field, Index, Relationship, SQLModel, text


class Visibility(str, Enum):
    draft = "draft"
    published = "published"


class CrumbTag(SQLModel, table=True):
    crumb_id: int = Field(
        foreign_key="crumb.id",
        primary_key=True,
    )
    tag_id: int = Field(
        foreign_key="tag.id",
        primary_key=True,
    )


# ---------- units ----------
class UnitBase(SQLModel, table=False):
    name: str = Field(
        max_length=100,
        description="Display name for this writing session"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this session was started"
    )


class Unit(UnitBase, table=True):
    __tablename__ = "unit"
    __table_args__ = (Index("idx_unit_name", "name"),)
    id: int | None = Field(default=None, primary_key=True)
    crumbs: list["Crumb"] = Relationship(
        back_populates="unit",
        sa_relationship_kwargs={
            "lazy": "selectin",
        },
    )

    def __str__(self) -> str:
        return f"Unit(id={self.id}, name={self.name}, created_at={self.created_at})"


class UnitCreate(UnitBase, table=False):
    pass


class UnitPublic(UnitBase, table=False):
    id: int


# ---------- crumbs ----------
class CrumbBase(SQLModel, table=False):
    body_md: str = Field(description="Markdown content of the crumb")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(
        default=None,
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}
    )
    visibility: Visibility = Field(
        default=Visibility.draft,
        description="The crumb's status (draft or published)"
    )


# The model for the persisted entity
class Crumb(CrumbBase, table=True):
    __tablename__ = "crumb"  # type: ignore
    __table_args__ = (Index("idx_crumb_created_at", "created_at"),)
    id: int | None = Field(default=None, primary_key=True)

    # Foreign key to unit (optional)
    unit_id: int | None = Field(default=None, foreign_key="unit.id")
    unit: Unit | None = Relationship(
        back_populates="crumbs",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    # Many-to-many relationship with tags
    tags: list["Tag"] = Relationship(
        back_populates="crumbs",
        link_model=CrumbTag,
        sa_relationship_kwargs={
            "lazy": "selectin",  # fetch related rows in a separate but efficient query using IN
            "passive_deletes": True,  # Defer delete handling to DB (requires ON DELETE CASCADE on the foreign key)
        },
    )

    def __str__(self) -> str:
        return (
            f"Crumb of id:{self.id}: {self.body_md[:10]}... created at: {self.created_at}"
        )


class CrumbCreate(CrumbBase, table=False):
    unit_name: str | None = Field(default=None, description="Optional unit name for grouping")
    tags: list["TagCreate"] = Field(default=[])


class CrumbPublic(CrumbBase, table=False):
    id: int
    unit: UnitPublic | None = None
    tags: list["TagPublic"] = Field(default=[])


# ---------- tags ----------
class TagBase(SQLModel, table=False):
    name: str = Field(
        index=True, min_length=1, max_length=50, description="Name of the tag"
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        v = re.sub(r"\s+", "-", v.strip().lower())
        v = re.sub(r"-{2,}", "-", v)  # collapse multiple dashes
        v = v.strip("-")  # no leading/trailing dashes
        if not re.match(r"^[a-z0-9\-]+$", v):
            raise ValueError("Tag names can only contain letters, numbers, and dashes")
        return v


class Tag(TagBase, table=True):
    __tablename__ = "tag"
    __table_args__ = (Index("uq_tag_name_lower_idx", text("lower(name)"), unique=True),)
    id: int | None = Field(default=None, primary_key=True)
    crumbs: list["Crumb"] = Relationship(
        back_populates="tags",
        link_model=CrumbTag,
        sa_relationship_kwargs={
            "lazy": "selectin",  # fetch related rows in a separate but efficient query using IN
            "passive_deletes": True,  # Defer delete handling to DB (requires ON DELETE CASCADE on the foreign key)
        },
    )

    @property
    def display_name(self) -> str:
        return self.name.replace("-", " ").title()


class TagCreate(TagBase):
    pass


class TagPublic(TagBase):
    id: int
