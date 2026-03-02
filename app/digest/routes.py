"""Weekly digest API endpoints for digests and subscribers."""

import hmac
import logging
import os
import secrets
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, col, select

from app.auth import require_admin
from app.db import get_session
from app.models import (
    Digest,
    DigestPublic,
    DigestStatus,
    DigestType,
    Subscriber,
)
from app.digest.email import send_confirmation_email
from app.digest.generate import (
    generate_digest,
    generate_monthly_digest,
    get_current_month_bounds,
    get_current_week_bounds,
)
from app.digest.send import send_digest_to_subscribers, send_test_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/digests", tags=["digests"])


# ---------- admin endpoints (list) ----------


@router.get("/admin", response_model=list[DigestPublic])
def list_all_digests(
    session: Session = Depends(get_session),
    _admin: None = Depends(require_admin),
    limit: int = Query(default=50, ge=1, le=100),
):
    """List all digests including drafts (admin only), newest first."""
    statement = (
        select(Digest)
        .order_by(col(Digest.period_start).desc())
        .limit(limit)
    )
    return session.exec(statement).all()


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
    digest_type: DigestType = Query(default=DigestType.weekly),
    session: Session = Depends(get_session),
    _admin: None = Depends(require_admin),
):
    """Generate a new digest for the given period (or auto-detect if omitted)."""
    if period_start is None or period_end is None:
        if digest_type == DigestType.monthly:
            period_start, period_end = get_current_month_bounds()
        else:
            period_start, period_end = get_current_week_bounds()

    # Check for existing digest of the same type
    existing = session.exec(
        select(Digest)
        .where(Digest.period_start == period_start)
        .where(Digest.digest_type == digest_type)
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"{digest_type.value.title()} digest already exists for {period_start.isoformat()} (id={existing.id})",
        )

    try:
        if digest_type == DigestType.monthly:
            digest = generate_monthly_digest(session, period_start, period_end)
        else:
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
        send_test_email(digest, req.email)
    except (RuntimeError, OSError) as e:
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
        if existing.is_active:
            return SubscribeResponse(message="Already subscribed.")
        if existing.unsubscribed_at:
            # Re-subscribe: reset state and send new confirmation.
            # Send email BEFORE committing state change so a Resend failure
            # doesn't leave the subscriber in a corrupted state.
            new_token = secrets.token_urlsafe(48)
            try:
                send_confirmation_email(email, new_token)
            except Exception:
                logger.error("Failed to send confirmation to %s", email, exc_info=True)
                raise HTTPException(status_code=502, detail="Could not send confirmation email. Please try again.")
            existing.unsubscribed_at = None
            existing.confirmed_at = None
            existing.confirmation_token = new_token
            session.add(existing)
            session.flush()
            return SubscribeResponse(message="Check your inbox.")
        # Not yet confirmed — resend
        try:
            send_confirmation_email(email, existing.confirmation_token)
        except Exception:
            logger.error("Failed to resend confirmation to %s", email, exc_info=True)
            raise HTTPException(status_code=502, detail="Could not send confirmation email. Please try again.")
        return SubscribeResponse(message="Check your inbox.")

    subscriber = Subscriber(
        email=email,
        confirmation_token=secrets.token_urlsafe(48),
        unsubscribe_token=secrets.token_urlsafe(48),
    )
    session.add(subscriber)
    session.flush()

    try:
        send_confirmation_email(email, subscriber.confirmation_token)
    except Exception:
        logger.error("Failed to send confirmation to %s", email, exc_info=True)
        raise HTTPException(status_code=502, detail="Could not send confirmation email. Please try again.")
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

    if not subscriber.is_confirmed:
        subscriber.confirmed_at = datetime.now(timezone.utc)
        session.add(subscriber)
        session.flush()

    return SubscribeResponse(message="Confirmed! You'll receive the next weekly digest.")


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
    action: Literal["created", "existed", "published_and_sent"]
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
    if not expected or not hmac.compare_digest(secret, expected):
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
    except ValueError as e:
        logger.warning("Cron digest generation skipped: %s", e)
        raise HTTPException(status_code=422, detail=str(e))

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
