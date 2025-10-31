from datetime import datetime, timezone
from enum import Enum
import re
from typing import List, Optional

from pydantic import field_validator
from sqlmodel import Field, Index, Relationship, SQLModel, text


class Visibility(str, Enum):
    draft = "draft"
    published = "published"


class CrumbTag(SQLModel, table=True):
    crumb_id: int = Field(
        foreign_key="crumb.id",
        primary_key=True,
        sa_column_kwargs={"ondelete": "CASCADE"},
    )
    tag_id: int = Field(
        foreign_key="tag.id",
        primary_key=True,
        sa_column_kwargs={"ondelete": "CASCADE"},
    )


# ---------- units ----------
class UnitBase(SQLModel, table=False):
    name: str = Field(
        max_length=100, description="Display name for this writing session"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this session was started",
    )


class Unit(UnitBase, table=True):
    __tablename__ = "unit"
    __table_args__ = (Index("idx_unit_name", "name"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    crumbs: List["Crumb"] = Relationship(  # type: ignore
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
    updated_at: Optional[datetime] = Field(
        default=None, sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}
    )
    visibility: Visibility = Field(
        default=Visibility.draft, description="The crumb's status (draft or published)"
    )


# The model for the persisted entity
class Crumb(CrumbBase, table=True):
    __tablename__ = "crumb"  # type: ignore
    __table_args__ = (Index("idx_crumb_created_at", "created_at"),)
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign key to unit (optional)
    unit_id: Optional[int] = Field(default=None, foreign_key="unit.id")
    unit: Optional["Unit"] = Relationship(
        back_populates="crumbs", sa_relationship_kwargs={"lazy": "selectin"}
    )

    # Many-to-many relationship with tags
    tags: List["Tag"] = Relationship(  # type: ignore
        back_populates="crumbs",
        link_model=CrumbTag,
        sa_relationship_kwargs={
            "lazy": "selectin",  # fetch related rows in a separate but efficient query using IN
            "passive_deletes": True,  # Defer delete handling to DB (requires ON DELETE CASCADE on the foreign key)
        },
    )

    def __str__(self) -> str:
        return f"Crumb of id:{self.id}: {self.body_md[:10]}... created at: {self.created_at}"


class CrumbCreate(CrumbBase, table=False):
    unit_name: Optional[str] = Field(
        default=None, description="Optional unit name for grouping"
    )
    tags: List["TagCreate"] = Field(default=[])


class CrumbPublic(CrumbBase, table=False):
    id: int
    unit: Optional["UnitPublic"] = None
    tags: List["TagPublic"] = Field(default=[])


# ---------- tags ----------
class TagBase(SQLModel, table=False):
    name: str = Field(
        index=True, min_length=1, max_length=50, description="Name of the tag"
    )

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Tag name cannot be empty")
        v = re.sub(r"\s+", "-", v.strip().lower())
        v = re.sub(r"-{2,}", "-", v)  # collapse multiple dashes
        v = v.strip("-")  # no leading/trailing dashes
        if not v:
            raise ValueError("Tag name cannot be empty after normalization")
        if not re.match(r"^[a-z0-9\-]+$", v):
            raise ValueError("Tag names can only contain letters, numbers, and dashes")
        return v


class Tag(TagBase, table=True):
    __tablename__ = "tag"
    __table_args__ = (Index("uq_tag_name_lower_idx", text("lower(name)"), unique=True),)
    id: Optional[int] = Field(default=None, primary_key=True)
    crumbs: List["Crumb"] = Relationship(  # type: ignore
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
