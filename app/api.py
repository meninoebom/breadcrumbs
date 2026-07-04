import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import nulls_last
from sqlalchemy.exc import DataError, IntegrityError, OperationalError
from starlette.requests import Request
from sqlmodel import Session, SQLModel, col, func, or_, select

import anthropic as anthropic_lib

from app.auth import create_access_token, require_admin, verify_admin_password
from app.db import get_session
from app.feed import months_to_collapse
from app.tag_suggester import suggest_tags
from app.images import (
    ImageCommitError,
    ImageGenerationError,
    ThemeImageService,
    default_theme_image_service,
)
from app.models import (
    Breadcrumb,
    BreadcrumbBase,
    BreadcrumbCreateInput,
    BreadcrumbPublic,
    Digest,
    DigestPublic,
    DigestType,
    MonthSummary,
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
from app.storage import R2ConfigError, put_object


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("ENABLE_SCHEDULER", "").lower() in ("true", "1"):
        from app.scheduler import start_scheduler, shutdown_scheduler

        start_scheduler()
        yield
        shutdown_scheduler()
    else:
        yield


app = FastAPI(title="Breadcrumbs API", lifespan=lifespan)

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
    # Compute next position once to avoid N+1 and concurrent duplicate positions.
    max_pos = session.exec(select(func.max(Tag.position))).first() or 0
    next_pos = max_pos + 1

    tags = []
    for tc in tag_creates:
        existing = session.exec(
            select(Tag).where(func.lower(Tag.name) == tc.name.lower())
        ).first()
        if existing:
            tags.append(existing)
        else:
            tag = Tag(name=tc.name, position=next_pos)
            next_pos += 1
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


# ---------- auth endpoints ----------


from pydantic import BaseModel as _BaseModel


class LoginRequest(_BaseModel):
    password: str


class LoginResponse(_BaseModel):
    access_token: str


@router.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    if not verify_admin_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_access_token()
    return LoginResponse(access_token=token)


# ---------- theme endpoints ----------


@router.post("/themes", response_model=ThemePublic, status_code=201)
def create_theme(
    theme_create: ThemeCreate,
    session: Session = Depends(get_session),
    _admin: None = Depends(require_admin),
):
    tags = get_or_create_tags(session, theme_create.tags)
    theme_data = theme_create.model_dump(exclude={"tags"})
    theme = Theme(**theme_data)
    theme.tags = tags
    session.add(theme)
    session.flush()
    session.refresh(theme)
    return theme


def _parse_month(month: str) -> tuple[date, date]:
    """Return (start, next_month_start) for a YYYY-MM string."""
    try:
        year_i, month_i = (int(x) for x in month.split("-"))
        start = date(year_i, month_i, 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="month must be YYYY-MM")
    if month_i == 12:
        end = date(year_i + 1, 1, 1)
    else:
        end = date(year_i, month_i + 1, 1)
    return start, end


@router.get("/themes", response_model=list[ThemePublic])
def list_themes(
    session: Session = Depends(get_session),
    visibility: Optional[Visibility] = None,
    tag: Optional[str] = None,
    q: Optional[str] = None,
    since: Optional[date] = None,
    month: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=500),
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

    if since is not None:
        since_dt = datetime.combine(since, time.min, tzinfo=timezone.utc)
        statement = statement.where(Theme.created_at >= since_dt)

    if month is not None:
        month_start, month_end = _parse_month(month)
        start_dt = datetime.combine(month_start, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(month_end, time.min, tzinfo=timezone.utc)
        statement = statement.where(Theme.created_at >= start_dt).where(
            Theme.created_at < end_dt
        )

    statement = statement.order_by(col(Theme.created_at).desc())

    # Scoped filters naturally bound their result sets; only paginate the
    # unscoped "give me everything" call so we don't silently truncate
    # a tag/search/month/since query.
    is_scoped = any(v is not None for v in (tag, q, since, month))
    if not is_scoped:
        statement = statement.offset(offset).limit(limit)

    themes = session.exec(statement).all()
    return themes


@router.get("/months", response_model=list[MonthSummary])
def list_months(session: Session = Depends(get_session)):
    """List past calendar months that should render as collapsed cards.

    A month is included iff every published theme in it falls outside the
    31-day rolling expanded window. Each entry includes theme count and the
    monthly digest covering that month (if one exists).
    """
    today = datetime.now(timezone.utc).date()

    theme_rows = session.exec(
        select(Theme.created_at).where(Theme.visibility == Visibility.published)
    ).all()
    theme_dates = [dt.date() for dt in theme_rows]

    collapsed = months_to_collapse(today, theme_dates)
    if not collapsed:
        return []

    # Count themes per (year, month) once.
    counts: dict[tuple[int, int], int] = {}
    for d in theme_dates:
        key = (d.year, d.month)
        counts[key] = counts.get(key, 0) + 1

    # Fetch any monthly digest whose period_start lies in one of the collapsed
    # months in a single query, then index by (year, month).
    monthly_digests = session.exec(
        select(Digest).where(Digest.digest_type == DigestType.monthly)
    ).all()
    digest_by_month: dict[tuple[int, int], Digest] = {}
    for digest in monthly_digests:
        key = (digest.period_start.year, digest.period_start.month)
        digest_by_month[key] = digest

    return [
        MonthSummary(
            year=year,
            month=month,
            theme_count=counts.get((year, month), 0),
            monthly_digest=(
                DigestPublic.model_validate(digest_by_month[(year, month)], from_attributes=True)
                if (year, month) in digest_by_month
                else None
            ),
        )
        for year, month in collapsed
    ]


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
    _admin: None = Depends(require_admin),
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
    _admin: None = Depends(require_admin),
):
    theme = session.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    session.delete(theme)
    session.flush()


# ---------- theme cover image endpoints ----------


class GenerateImageResponse(SQLModel):
    prompt: str
    candidates: List[str]


class CommitImageRequest(SQLModel):
    source_url: str


@router.post("/themes/{theme_id}/generate-image", response_model=GenerateImageResponse)
def generate_theme_image(
    theme_id: int,
    session: Session = Depends(get_session),
    service: ThemeImageService = Depends(default_theme_image_service),
    _admin: None = Depends(require_admin),
):
    theme = session.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    try:
        result = service.generate_candidates(
            theme_body=theme.body_md,
            tag_names=[t.name for t in theme.tags],
            breadcrumb_bodies=[
                b.body_md
                for b in sorted(theme.breadcrumbs, key=lambda b: b.created_at)
            ],
        )
    except ImageGenerationError as e:
        logger.warning("Image generation failed for theme %d: %s", theme_id, e)
        raise HTTPException(status_code=503, detail=str(e))

    return GenerateImageResponse(prompt=result.prompt, candidates=result.candidates)


@router.post("/themes/{theme_id}/image", response_model=ThemePublic)
def commit_theme_image(
    theme_id: int,
    body: CommitImageRequest,
    session: Session = Depends(get_session),
    service: ThemeImageService = Depends(default_theme_image_service),
    _admin: None = Depends(require_admin),
):
    theme = session.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    try:
        theme.image_url = service.commit_candidate(body.source_url)
    except ImageCommitError as e:
        logger.warning("Image commit failed for theme %d: %s", theme_id, e)
        raise HTTPException(status_code=400, detail=str(e))
    except R2ConfigError as e:
        logger.error("R2 misconfigured during commit for theme %d: %s", theme_id, e)
        raise HTTPException(status_code=500, detail="Storage is misconfigured")

    session.add(theme)
    session.flush()
    session.refresh(theme)
    return theme


@router.delete("/themes/{theme_id}/image", response_model=ThemePublic)
def clear_theme_image(
    theme_id: int,
    session: Session = Depends(get_session),
    _admin: None = Depends(require_admin),
):
    theme = session.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    theme.image_url = None
    session.add(theme)
    session.flush()
    session.refresh(theme)
    return theme


# ---------- tag suggestion endpoint ----------


class SuggestTagsResponse(SQLModel, table=False):
    tags: List[str]


@router.post("/themes/{theme_id}/suggest-tags", response_model=SuggestTagsResponse)
def suggest_theme_tags(
    theme_id: int,
    session: Session = Depends(get_session),
    _admin: None = Depends(require_admin),
):
    theme = session.get(Theme, theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    existing_tag_names = [t.name for t in session.exec(select(Tag)).all()]

    try:
        tags = suggest_tags(theme.body_md, existing_tag_names)
    except anthropic_lib.APIError as e:
        logger.warning("Tag suggestion failed for theme %d: %s", theme_id, e)
        raise HTTPException(status_code=503, detail="Tag suggestion service unavailable")

    return SuggestTagsResponse(tags=tags)


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
    _admin: None = Depends(require_admin),
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
    _admin: None = Depends(require_admin),
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
    _admin: None = Depends(require_admin),
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
        .order_by(nulls_last(Tag.position), Tag.name)
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


class TagReorderRequest(SQLModel, table=False):
    tag_ids: List[int]


@router.patch("/tags/reorder", status_code=200)
def reorder_tags(
    body: TagReorderRequest,
    session: Session = Depends(get_session),
    _: None = Depends(require_admin),
):
    """Assign server-side positions to tags based on the supplied ordered list."""
    for position, tag_id in enumerate(body.tag_ids):
        tag = session.get(Tag, tag_id)
        if tag is not None:
            tag.position = position
            session.add(tag)
    session.commit()
    return {"ok": True}


# ---------- image uploads ----------

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/uploads")
def upload_image(
    file: UploadFile = File(...),
    _admin: None = Depends(require_admin),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"Unsupported image type: {file.content_type}")

    contents = file.file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (10MB max)")

    ext = os.path.splitext(file.filename or "")[1] or ".png"
    key = f"{uuid.uuid4().hex[:12]}{ext}"

    try:
        url = put_object(key, contents, file.content_type)
    except R2ConfigError as e:
        logger.error("R2 misconfigured during upload: %s", e)
        raise HTTPException(status_code=500, detail="Storage is misconfigured")
    return {"url": url}


# ---------- app assembly ----------

from app.digest.routes import cron_router, router as digest_router, subscriber_router

app.include_router(router)
app.include_router(digest_router)
app.include_router(subscriber_router)
app.include_router(cron_router)

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
