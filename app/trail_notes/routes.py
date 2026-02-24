"""Trail Notes API endpoints for digests and subscribers."""

import os
import secrets
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, col, select

from app.auth import require_admin
from app.db import get_session
from app.models import (
    Digest,
    DigestPublic,
    DigestStatus,
    Subscriber,
    SubscriberCreate,
)
from app.trail_notes.email import send_confirmation_email
from app.trail_notes.generate import generate_digest, get_current_week_bounds
from app.trail_notes.send import send_digest_to_subscribers, send_test_email

router = APIRouter(prefix="/api/digests", tags=["trail-notes"])


# ---------- public endpoints ----------


@router.get("", response_model=list[DigestPublic])
def list_digests(
    session: Session = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List published digests, newest first."""
    statement = (
        select(Digest)
        .where(Digest.status.in_([DigestStatus.published, DigestStatus.sent]))  # type: ignore[attr-defined]
        .order_by(col(Digest.period_start).desc())
        .offset(offset)
        .limit(limit)
    )
    return session.exec(statement).all()


@router.get("/{digest_id}", response_model=DigestPublic)
def get_digest(
    digest_id: int,
    session: Session = Depends(get_session),
):
    digest = session.get(Digest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    # Allow viewing drafts only if they exist (admin can share links)
    return digest


# ---------- admin endpoints ----------


@router.post("/generate", response_model=DigestPublic, status_code=201)
def generate_digest_endpoint(
    period_start: date = Query(default=None),
    period_end: date = Query(default=None),
    session: Session = Depends(get_session),
    _admin: None = Depends(require_admin),
):
    """Generate a new digest for the given week (or last week if omitted)."""
    if period_start is None or period_end is None:
        period_start, period_end = get_current_week_bounds()

    # Check for existing digest
    existing = session.exec(
        select(Digest).where(Digest.period_start == period_start)
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Digest already exists for week of {period_start.isoformat()} (id={existing.id})",
        )

    try:
        digest = generate_digest(session, period_start, period_end)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return digest


@router.post("/{digest_id}/publish", response_model=DigestPublic)
def publish_digest(
    digest_id: int,
    session: Session = Depends(get_session),
    _admin: None = Depends(require_admin),
):
    """Move a digest from draft to published (visible on archive)."""
    digest = session.get(Digest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    if digest.status != DigestStatus.draft:
        raise HTTPException(status_code=400, detail=f"Digest is already {digest.status.value}")

    digest.status = DigestStatus.published
    session.add(digest)
    session.flush()
    session.refresh(digest)
    return digest


class SendResponse(BaseModel):
    sent: int
    failed: int
    skipped: int


@router.post("/{digest_id}/send", response_model=SendResponse)
def send_digest_endpoint(
    digest_id: int,
    session: Session = Depends(get_session),
    _admin: None = Depends(require_admin),
):
    """Send a published digest to all confirmed subscribers."""
    digest = session.get(Digest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    if digest.status == DigestStatus.draft:
        raise HTTPException(status_code=400, detail="Publish the digest before sending.")
    if digest.status == DigestStatus.sent:
        raise HTTPException(status_code=400, detail="Digest has already been sent.")

    result = send_digest_to_subscribers(session, digest)
    return SendResponse(**result)


class SendTestRequest(BaseModel):
    email: EmailStr


@router.post("/{digest_id}/send-test")
def send_test_endpoint(
    digest_id: int,
    req: SendTestRequest,
    session: Session = Depends(get_session),
    _admin: None = Depends(require_admin),
):
    """Send a test email for QA (any digest status)."""
    digest = session.get(Digest, digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")

    try:
        send_test_email(session, digest, req.email)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to send test email: {e}")

    return {"message": f"Test email sent to {req.email}"}


# ---------- subscriber endpoints ----------


subscriber_router = APIRouter(prefix="/api/subscribers", tags=["subscribers"])


class SubscribeRequest(BaseModel):
    email: EmailStr


class SubscribeResponse(BaseModel):
    message: str


@subscriber_router.post("/subscribe", response_model=SubscribeResponse)
def subscribe(
    req: SubscribeRequest,
    session: Session = Depends(get_session),
):
    """Subscribe an email. Sends confirmation link (double opt-in)."""
    email = req.email.lower().strip()

    existing = session.exec(
        select(Subscriber).where(Subscriber.email == email)
    ).first()

    if existing:
        if existing.confirmed and not existing.unsubscribed_at:
            return SubscribeResponse(message="Already subscribed.")
        if existing.unsubscribed_at:
            # Re-subscribe: reset state and send new confirmation
            existing.unsubscribed_at = None
            existing.confirmed = False
            existing.confirmed_at = None
            existing.confirmation_token = secrets.token_urlsafe(48)
            session.add(existing)
            session.flush()
            send_confirmation_email(email, existing.confirmation_token)
            return SubscribeResponse(message="Check your inbox.")
        # Not yet confirmed — resend
        send_confirmation_email(email, existing.confirmation_token)
        return SubscribeResponse(message="Check your inbox.")

    subscriber = Subscriber(
        email=email,
        confirmed=False,
        confirmation_token=secrets.token_urlsafe(48),
        unsubscribe_token=secrets.token_urlsafe(48),
    )
    session.add(subscriber)
    session.flush()

    send_confirmation_email(email, subscriber.confirmation_token)
    return SubscribeResponse(message="Check your inbox.")


@subscriber_router.get("/confirm", response_model=SubscribeResponse)
def confirm_subscription(
    token: str = Query(...),
    session: Session = Depends(get_session),
):
    """Confirm a subscription via token from the confirmation email."""
    subscriber = session.exec(
        select(Subscriber).where(Subscriber.confirmation_token == token)
    ).first()

    if not subscriber:
        raise HTTPException(status_code=404, detail="Invalid or expired confirmation link.")

    if not subscriber.confirmed:
        subscriber.confirmed = True
        subscriber.confirmed_at = datetime.now(timezone.utc)
        session.add(subscriber)
        session.flush()

    return SubscribeResponse(message="Confirmed! You'll receive the next Trail Note.")


@subscriber_router.get("/unsubscribe", response_model=SubscribeResponse)
def unsubscribe(
    token: str = Query(...),
    session: Session = Depends(get_session),
):
    """Unsubscribe via permanent token in email footer."""
    subscriber = session.exec(
        select(Subscriber).where(Subscriber.unsubscribe_token == token)
    ).first()

    if not subscriber:
        raise HTTPException(status_code=404, detail="Invalid unsubscribe link.")

    if not subscriber.unsubscribed_at:
        subscriber.unsubscribed_at = datetime.now(timezone.utc)
        session.add(subscriber)
        session.flush()

    return SubscribeResponse(message="You've been unsubscribed. No hard feelings.")


# ---------- cron endpoint ----------


cron_router = APIRouter(prefix="/api/internal", tags=["internal"])


class CronResponse(BaseModel):
    digest: DigestPublic
    action: str  # "created", "existed", "published_and_sent"
    send_result: SendResponse | None = None


@cron_router.post("/weekly-digest", response_model=CronResponse, status_code=201)
def cron_weekly_digest(
    secret: str = Query(...),
    auto_send: bool = Query(default=False),
    session: Session = Depends(get_session),
):
    """Called by Railway Cron to auto-generate (and optionally send) the weekly digest.

    - Default: generates a draft for manual review.
    - auto_send=true: generates, publishes, and sends in one shot.
    """
    expected = os.getenv("CRON_SECRET", "")
    if not expected or secret != expected:
        raise HTTPException(status_code=403, detail="Invalid cron secret")

    period_start, period_end = get_current_week_bounds()

    # Idempotent: skip generation if already exists
    existing = session.exec(
        select(Digest).where(Digest.period_start == period_start)
    ).first()

    if existing:
        return CronResponse(digest=DigestPublic.model_validate(existing), action="existed")

    try:
        digest = generate_digest(session, period_start, period_end)
    except ValueError:
        raise HTTPException(status_code=422, detail="No content this week — skipping.")

    if not auto_send:
        return CronResponse(digest=DigestPublic.model_validate(digest), action="created")

    # Auto-publish and send
    digest.status = DigestStatus.published
    session.add(digest)
    session.flush()

    result = send_digest_to_subscribers(session, digest)
    session.refresh(digest)

    return CronResponse(
        digest=DigestPublic.model_validate(digest),
        action="published_and_sent",
        send_result=SendResponse(**result),
    )
