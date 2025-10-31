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
        sa_column_kwargs={"ondelete": "CASCADE"},
    )
    tag_id: int = Field(
        foreign_key="tag.id",
        primary_key=True,
        sa_column_kwargs={"ondelete": "CASCADE"},
    )


# ---------- crumbs ----------
class CrumbBase(SQLModel, table=False):
    body: str = Field(description="The content of the crumb")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(default=None)
    visibility: Visibility = Field(
        description="The crumb's status (draft or published etc.)"
    )


# The model for the persisted entity
class Crumb(CrumbBase, table=True):
    __tablename__ = "crumb"  # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    tags: list["Tag"] = Relationship(
        back_populates="crumbs",
        link_model=CrumbTag,
        repr=False,
        sa_relationship_kwargs={
            "lazy": "selectin",  # fetch related rows in a separate but efficient query using IN
            "passive_deletes": True,  # Defer delete handling to DB (requires ON DELETE CASCADE on the foreign key)
        },
    )

    def __str__(self) -> str:
        return (
            f"Crumb of id:{self.id}: {self.body[:10]}... created at: {self.created_at}"
        )


class CrumbCreate(CrumbBase, table=False):
    tags: list["TagCreate"] = Field(default=[])


class CrumbPublic(CrumbBase, table=False):
    id: int
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
        repr=False,
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
