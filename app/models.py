from datetime import date, datetime, timezone
from enum import Enum
import re
from typing import List, Optional

from pydantic import field_validator
from sqlmodel import Field, Index, Relationship, SQLModel, UniqueConstraint, text


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
    body_md: str = Field(min_length=1, description="Markdown content of the thought")
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
    id: Optional[int] = Field(default=None, primary_key=True)
    breadcrumbs: List["Breadcrumb"] = Relationship(  # type: ignore
        back_populates="theme",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    # Many-to-many relationship with tags
    tags: List["Tag"] = Relationship(  # type: ignore
        back_populates="themes",
        link_model=ThemeTag,
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "save-update, merge",
            "passive_deletes": True,
        },
    )

    def __str__(self) -> str:
        preview = self.body_md[:40] if self.body_md else ""
        return f"Theme(id={self.id}, body={preview!r}, visibility={self.visibility})"


class ThemeCreate(ThemeBase, table=False):
    tags: List["TagCreate"] = Field(default=[])


class ThemeUpdate(SQLModel, table=False):
    body_md: Optional[str] = None
    visibility: Optional[Visibility] = None
    tags: Optional[List["TagCreate"]] = None


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
        back_populates="breadcrumbs",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    # Optional parent breadcrumb (self-referential, adjacency list pattern)
    parent_id: Optional[int] = Field(
        default=None,
        foreign_key="breadcrumb.id",
        ondelete="CASCADE",
    )
    parent: Optional["Breadcrumb"] = Relationship(  # type: ignore
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "Breadcrumb.id",
            "lazy": "noload",
        },
    )
    children: List["Breadcrumb"] = Relationship(  # type: ignore
        back_populates="parent",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "lazy": "noload",
        },
    )

    def __str__(self) -> str:
        return f"Breadcrumb of id:{self.id}: {self.body_md[:10]}... created at: {self.created_at}"


class BreadcrumbCreateInput(SQLModel, table=False):
    """Request body for POST /themes/{theme_id}/breadcrumbs."""
    body_md: str = Field(min_length=1, description="Markdown content of the breadcrumb")
    parent_id: Optional[int] = Field(
        default=None, ge=1, description="Optional parent breadcrumb ID"
    )


class BreadcrumbPublic(BreadcrumbBase, table=False):
    id: int
    parent_id: Optional[int] = None
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
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "save-update, merge",
            "passive_deletes": True,
        },
    )

    @property
    def display_name(self) -> str:
        return self.name.replace("-", " ").title()


class TagCreate(TagBase):
    pass


class TagPublic(TagBase):
    id: int


class TagWithCount(SQLModel, table=False):
    id: int
    name: str
    theme_count: int


# ---------- weekly digest ----------


class DigestType(str, Enum):
    weekly = "weekly"
    monthly = "monthly"


class DigestStatus(str, Enum):
    draft = "draft"
    published = "published"
    sent = "sent"


class Digest(SQLModel, table=True):
    __tablename__ = "digest"
    __table_args__ = (
        UniqueConstraint("period_start", "digest_type", name="uq_digest_period_start_type"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(description="Digest title / headline")
    summary_md: str = Field(description="Full digest prose in markdown")
    digest_type: DigestType = Field(default=DigestType.weekly, description="weekly or monthly")
    period_start: date = Field(description="Start of the period this digest covers")
    period_end: date = Field(description="End of the period this digest covers")
    status: DigestStatus = Field(default=DigestStatus.draft)
    sent_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: Optional[datetime] = Field(
        default=None, sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)}
    )

    sends: List["DigestSend"] = Relationship(  # type: ignore
        back_populates="digest",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
            "lazy": "selectin",
        },
    )


class DigestPublic(SQLModel, table=False):
    id: int
    title: str
    summary_md: str
    digest_type: DigestType = DigestType.weekly
    period_start: date
    period_end: date
    status: DigestStatus
    sent_at: Optional[datetime] = None
    created_at: datetime


class DigestCreate(SQLModel, table=False):
    title: str = Field(min_length=1)
    summary_md: str = Field(min_length=1)
    period_start: date
    period_end: date


# ---------- subscribers ----------


class Subscriber(SQLModel, table=True):
    __tablename__ = "subscriber"
    __table_args__ = (
        UniqueConstraint("email", name="uq_subscriber_email"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(max_length=320, description="Subscriber email address")
    confirmation_token: str = Field(max_length=128, index=True)
    unsubscribe_token: str = Field(max_length=128, index=True)
    confirmed_at: Optional[datetime] = Field(default=None)
    unsubscribed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    @property
    def is_confirmed(self) -> bool:
        return self.confirmed_at is not None

    @property
    def is_active(self) -> bool:
        return self.confirmed_at is not None and self.unsubscribed_at is None


class SubscriberCreate(SQLModel, table=False):
    email: str = Field(max_length=320, min_length=5)


# ---------- digest sends ----------


class SendStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class DigestSend(SQLModel, table=True):
    __tablename__ = "digest_send"
    __table_args__ = (
        UniqueConstraint("digest_id", "subscriber_id", name="uq_digest_send_digest_subscriber"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    digest_id: int = Field(foreign_key="digest.id", ondelete="CASCADE")
    subscriber_id: int = Field(foreign_key="subscriber.id", ondelete="CASCADE")
    status: SendStatus = Field(default=SendStatus.pending)
    sent_at: Optional[datetime] = Field(default=None)

    digest: "Digest" = Relationship(  # type: ignore
        back_populates="sends",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    subscriber: "Subscriber" = Relationship(  # type: ignore
        sa_relationship_kwargs={"lazy": "selectin"},
    )
