"""Send a published digest to all confirmed subscribers."""

import logging
from datetime import datetime, timezone

import mistune
from tenacity import retry, stop_after_attempt, wait_exponential

from sqlmodel import Session, select

from app.models import (
    Digest,
    DigestSend,
    DigestStatus,
    SendStatus,
    Subscriber,
)
from app.trail_notes.email import send_digest_email

logger = logging.getLogger(__name__)


def markdown_to_html(md: str) -> str:
    """Convert markdown prose to simple HTML for email."""
    return mistune.html(md)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def _send_one(
    email: str,
    unsubscribe_token: str,
    digest_title: str,
    digest_html: str,
    digest_id: int,
) -> None:
    send_digest_email(email, unsubscribe_token, digest_title, digest_html, digest_id)


def send_digest_to_subscribers(session: Session, digest: Digest) -> dict:
    """Send a digest to all confirmed, non-unsubscribed subscribers.

    Creates DigestSend records to track delivery. Skips subscribers
    who already have a send record (idempotent).

    Returns a summary dict with sent/failed/skipped counts.
    """
    digest_html = markdown_to_html(digest.summary_md)

    subscribers = session.exec(
        select(Subscriber)
        .where(Subscriber.confirmed == True)  # noqa: E712
        .where(Subscriber.unsubscribed_at == None)  # noqa: E711
    ).all()

    sent = 0
    failed = 0
    skipped = 0

    for sub in subscribers:
        # Check for existing send record (idempotent)
        existing = session.exec(
            select(DigestSend)
            .where(DigestSend.digest_id == digest.id)
            .where(DigestSend.subscriber_id == sub.id)
        ).first()
        if existing:
            skipped += 1
            continue

        send_record = DigestSend(
            digest_id=digest.id,
            subscriber_id=sub.id,
            status=SendStatus.pending,
        )
        session.add(send_record)
        session.flush()

        try:
            _send_one(
                email=sub.email,
                unsubscribe_token=sub.unsubscribe_token,
                digest_title=digest.title,
                digest_html=digest_html,
                digest_id=digest.id,
            )
            send_record.status = SendStatus.sent
            send_record.sent_at = datetime.now(timezone.utc)
            sent += 1
        except Exception as e:
            logger.error("Failed to send digest %d to %s: %s", digest.id, sub.email, e)
            send_record.status = SendStatus.failed
            failed += 1

        session.add(send_record)
        session.flush()

    # Only mark as sent if at least one email was delivered.
    # If all failed, leave as published so admin can retry.
    if sent > 0:
        digest.status = DigestStatus.sent
        digest.sent_at = datetime.now(timezone.utc)
        session.add(digest)
        session.flush()
    elif failed > 0:
        logger.error(
            "Digest %d: all %d sends failed, leaving as published for retry",
            digest.id, failed,
        )

    return {"sent": sent, "failed": failed, "skipped": skipped}


def send_test_email(session: Session, digest: Digest, email: str) -> None:
    """Send a single test email for QA (doesn't create DigestSend records)."""
    digest_html = markdown_to_html(digest.summary_md)
    # Use a dummy unsubscribe token for test emails
    send_digest_email(
        email=email,
        unsubscribe_token="test-preview",
        digest_title=f"[TEST] {digest.title}",
        digest_html=digest_html,
        digest_id=digest.id,
    )
