import logging
import os
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import DataError, IntegrityError, OperationalError
from starlette.requests import Request
from sqlmodel import Session, col, func, or_, select

from app.db import get_session
from app.models import (
    Breadcrumb,
    BreadcrumbBase,
    BreadcrumbCreateInput,
    BreadcrumbPublic,
    Tag,
    TagCreate,
    TagWithCount,
    Theme,
    ThemeCreate,
    ThemePublic,
    ThemeTag,
    ThemeUpdate,
    Visibility,
)

app = FastAPI(title="Breadcrumbs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)


@app.exception_handler(IntegrityError)
def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.error("IntegrityError: %s", exc)
    return JSONResponse(status_code=409, content={"detail": "Conflict: a database constraint was violated"})


@app.exception_handler(OperationalError)
def operational_error_handler(request: Request, exc: OperationalError):
    logger.error("OperationalError: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "Service temporarily unavailable"})


@app.exception_handler(DataError)
def data_error_handler(request: Request, exc: DataError):
    logger.error("DataError: %s", exc)
    return JSONResponse(status_code=400, content={"detail": "Invalid data submitted"})


THEME_UPDATABLE_FIELDS = {"body_md", "visibility"}


# ---------- helpers ----------


def escape_like(s: str) -> str:
    """Escape LIKE/ILIKE wildcard characters so they match literally."""
    return re.sub(r"([%_\\])", r"\\\1", s)


def get_or_create_tags(session: Session, tag_creates: list[TagCreate]) -> list[Tag]:
    """Find existing tags by normalized name, or create new ones."""
    tags = []
    for tc in tag_creates:
        existing = session.exec(
            select(Tag).where(func.lower(Tag.name) == tc.name.lower())
        ).first()
        if existing:
            tags.append(existing)
        else:
            tag = Tag(name=tc.name)
            session.add(tag)
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
                existing = session.exec(
                    select(Tag).where(func.lower(Tag.name) == tc.name.lower())
                ).first()
                if not existing:
                    raise
                tags.append(existing)
                continue
            tags.append(tag)
    return tags


# ---------- theme endpoints ----------


@router.post("/themes", response_model=ThemePublic, status_code=201)
def create_theme(
    theme_create: ThemeCreate,
    session: Session = Depends(get_session),
):
    tags = get_or_create_tags(session, theme_create.tags)
    theme_data = theme_create.model_dump(exclude={"tags"})
    theme = Theme(**theme_data)
    theme.tags = tags
    session.add(theme)
    session.flush()
    session.refresh(theme)
    return theme


@router.get("/themes", response_model=list[ThemePublic])
def list_themes(
    session: Session = Depends(get_session),
    visibility: Optional[Visibility] = None,
    tag: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    statement = select(Theme)

    if visibility:
        statement = statement.where(Theme.visibility == visibility)

    if tag:
        statement = statement.join(Theme.tags).where(
            func.lower(Tag.name) == tag.lower()
        )

    if q:
        safe_q = escape_like(q)
        statement = statement.where(
            or_(
                col(Theme.body_md).ilike(f"%{safe_q}%"),
                Theme.breadcrumbs.any(col(Breadcrumb.body_md).ilike(f"%{safe_q}%")),
            )
        )

    statement = statement.order_by(col(Theme.created_at).desc())
    statement = statement.offset(offset).limit(limit)

    themes = session.exec(statement).all()
    return themes


@router.get("/themes/{theme_id}", response_model=ThemePublic)
def get_theme(
    theme_id: int,
    session: Session = Depends(get_session),
):
    theme = session.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    return theme


@router.put("/themes/{theme_id}", response_model=ThemePublic)
def update_theme(
    theme_id: int,
    theme_update: ThemeUpdate,
    session: Session = Depends(get_session),
):
    theme = session.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    update_data = theme_update.model_dump(exclude_unset=True, exclude={"tags"})
    for key, value in update_data.items():
        if key not in THEME_UPDATABLE_FIELDS:
            raise HTTPException(status_code=400, detail=f"Cannot update field '{key}'")
        setattr(theme, key, value)

    if theme_update.tags is not None:
        theme.tags = get_or_create_tags(session, theme_update.tags)

    session.add(theme)
    session.flush()
    session.refresh(theme)
    return theme


@router.delete("/themes/{theme_id}", status_code=204)
def delete_theme(
    theme_id: int,
    session: Session = Depends(get_session),
):
    theme = session.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    session.delete(theme)
    session.flush()


# ---------- breadcrumb endpoints ----------


@router.post(
    "/themes/{theme_id}/breadcrumbs",
    response_model=BreadcrumbPublic,
    status_code=201,
)
def create_breadcrumb(
    theme_id: int,
    breadcrumb_in: BreadcrumbCreateInput,
    session: Session = Depends(get_session),
):
    theme = session.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    if breadcrumb_in.parent_id is not None:
        parent = session.get(Breadcrumb, breadcrumb_in.parent_id)
        if not parent:
            raise HTTPException(
                status_code=400, detail="Parent breadcrumb not found"
            )
        if parent.theme_id != theme_id:
            raise HTTPException(
                status_code=400,
                detail="Parent breadcrumb belongs to a different theme",
            )
        # Walk up ancestor chain to enforce depth limit.
        # depth counts edges from root to the new node: root=0, child=1, ...
        # We reject if the new node would be at depth >= 10.
        depth = 1
        ancestor = parent
        while ancestor.parent_id is not None:
            depth += 1
            if depth >= 10:
                raise HTTPException(
                    status_code=400, detail="Maximum nesting depth (10) exceeded"
                )
            ancestor = session.get(Breadcrumb, ancestor.parent_id)
            if ancestor is None:
                break  # orphaned FK — shouldn't happen with CASCADE

    breadcrumb = Breadcrumb(
        body_md=breadcrumb_in.body_md,
        theme_id=theme_id,
        parent_id=breadcrumb_in.parent_id,
    )
    session.add(breadcrumb)
    session.flush()
    session.refresh(breadcrumb)
    return breadcrumb


@router.get(
    "/themes/{theme_id}/breadcrumbs",
    response_model=list[BreadcrumbPublic],
)
def list_breadcrumbs(
    theme_id: int,
    session: Session = Depends(get_session),
):
    theme = session.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    statement = (
        select(Breadcrumb)
        .where(Breadcrumb.theme_id == theme_id)
        .order_by(col(Breadcrumb.created_at))
    )
    breadcrumbs = session.exec(statement).all()
    return breadcrumbs


@router.put(
    "/themes/{theme_id}/breadcrumbs/{breadcrumb_id}",
    response_model=BreadcrumbPublic,
)
def update_breadcrumb(
    theme_id: int,
    breadcrumb_id: int,
    breadcrumb_in: BreadcrumbBase,
    session: Session = Depends(get_session),
):
    breadcrumb = session.get(Breadcrumb, breadcrumb_id)
    if not breadcrumb or breadcrumb.theme_id != theme_id:
        raise HTTPException(status_code=404, detail="Breadcrumb not found")

    breadcrumb.body_md = breadcrumb_in.body_md
    session.add(breadcrumb)
    session.flush()
    session.refresh(breadcrumb)
    return breadcrumb


@router.delete(
    "/themes/{theme_id}/breadcrumbs/{breadcrumb_id}",
    status_code=204,
)
def delete_breadcrumb(
    theme_id: int,
    breadcrumb_id: int,
    session: Session = Depends(get_session),
):
    breadcrumb = session.get(Breadcrumb, breadcrumb_id)
    if not breadcrumb or breadcrumb.theme_id != theme_id:
        raise HTTPException(status_code=404, detail="Breadcrumb not found")
    session.delete(breadcrumb)
    session.flush()


# ---------- tag endpoints ----------


@router.get("/tags", response_model=list[TagWithCount])
def list_tags(session: Session = Depends(get_session)):
    statement = (
        select(Tag, func.count(ThemeTag.theme_id).label("theme_count"))
        .outerjoin(ThemeTag, Tag.id == ThemeTag.tag_id)
        .group_by(Tag.id)
        .order_by(Tag.name)
    )
    results = session.exec(statement).all()
    return [
        TagWithCount(id=tag.id, name=tag.name, theme_count=count)
        for tag, count in results
    ]


@router.get("/tags/{tag_name}/themes", response_model=list[ThemePublic])
def get_themes_by_tag(
    tag_name: str,
    session: Session = Depends(get_session),
):
    tag = session.exec(
        select(Tag).where(func.lower(Tag.name) == tag_name.lower())
    ).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag.themes


# ---------- app assembly ----------

app.include_router(router)

# In production, serve the built frontend
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if ENVIRONMENT == "production" and STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(STATIC_DIR / "index.html")
