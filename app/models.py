from datetime import datetime, timezone
from enum import Enum
import re
from typing import List, Optional

from pydantic import field_validator
from sqlmodel import Field, Index, Relationship, SQLModel, text


class Visibility(str, Enum):
    draft = "draft"
    published = "published"


class ThemeTag(SQLModel, table=True):
    __tablename__ = "theme_tag"
    theme_id: int = Field(
        foreign_key="theme.id",
        primary_key=True,
        ondelete="CASCADE",
    )
    tag_id: int = Field(
        foreign_key="tag.id",
        primary_key=True,
        index=True,
        ondelete="CASCADE",
    )


# ---------- themes ----------
class ThemeBase(SQLModel, table=False):
    title: str = Field(
        max_length=200, description="Theme title"
    )
    description_md: Optional[str] = Field(
        default=None, description="Optional theme intro/context"
    )
    visibility: Visibility = Field(
        default=Visibility.draft, description="The theme's status (draft or published)"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this theme was created",
    )
    updated_at: Optional[datetime] = Field(
        default=None, sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}
    )


class Theme(ThemeBase, table=True):
    __tablename__ = "theme"
    __table_args__ = (Index("idx_theme_title", "title"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    breadcrumbs: List["Breadcrumb"] = Relationship(  # type: ignore
        back_populates="theme",
        cascade_delete=True, 
        sa_relationship_kwargs={
            "lazy": "selectin",
        },
    )
    # Many-to-many relationship with tags
    tags: List["Tag"] = Relationship(  # type: ignore
        back_populates="themes",
        link_model=ThemeTag,
        cascade_delete=True, 
        sa_relationship_kwargs={
            "lazy": "selectin",
        },
    )

    def __str__(self) -> str:
        return f"Theme(id={self.id}, title={self.title}, visibility={self.visibility})"


class ThemeCreate(ThemeBase, table=False):
    tags: List["TagCreate"] = Field(default=[])


class ThemePublic(ThemeBase, table=False):
    id: int
    tags: List["TagPublic"] = Field(default=[])


# ---------- breadcrumbs ----------
class BreadcrumbBase(SQLModel, table=False):
    body_md: str = Field(description="Markdown content of the breadcrumb")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(
        default=None, sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}
    )


# The model for the persisted entity
class Breadcrumb(BreadcrumbBase, table=True):
    __tablename__ = "breadcrumb"  # type: ignore
    __table_args__ = (Index("idx_breadcrumb_created_at", "created_at"),)
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign key to theme (required)
    theme_id: int = Field(foreign_key="theme.id", ondelete="CASCADE")
    theme: "Theme" = Relationship(
        back_populates="breadcrumbs", sa_relationship_kwargs={"lazy": "selectin"}
    )

    def __str__(self) -> str:
        return f"Breadcrumb of id:{self.id}: {self.body_md[:10]}... created at: {self.created_at}"


class BreadcrumbCreate(BreadcrumbBase, table=False):
    theme_id: int = Field(description="Required theme ID for this breadcrumb")


class BreadcrumbPublic(BreadcrumbBase, table=False):
    id: int
    theme: Optional["ThemePublic"] = None  # type: ignore


# ---------- tags ----------
class TagBase(SQLModel, table=False):
    name: str = Field(
        min_length=1, max_length=50, description="Name of the tag"
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
    themes: List["Theme"] = Relationship(  # type: ignore
        back_populates="tags",
        link_model=ThemeTag,
        cascade_delete=True, 
        sa_relationship_kwargs={
            "lazy": "selectin",  # fetch related rows in a separate but efficient query using IN
        },
    )

    @property
    def display_name(self) -> str:
        return self.name.replace("-", " ").title()


class TagCreate(TagBase):
    pass


class TagPublic(TagBase):
    id: int
