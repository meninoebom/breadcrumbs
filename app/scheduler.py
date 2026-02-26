"""In-process weekly digest scheduler using APScheduler.

Two jobs:
- Sunday 2pm UTC (6am PT): generate a draft digest for the past week
- Tuesday 2pm UTC (6am PT): publish the draft and send to subscribers
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, col, select

from app.db import engine
from app.digest.generate import generate_digest, get_current_week_bounds
from app.digest.send import send_digest_to_subscribers
from app.models import Digest, DigestStatus

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def scheduled_generate():
    """Generate a draft digest for the most recently completed week."""
    period_start, period_end = get_current_week_bounds()

    with Session(engine) as session:
        existing = session.exec(
            select(Digest).where(Digest.period_start == period_start)
        ).first()
        if existing:
            logger.info("Digest already exists for week of %s (id=%d), skipping", period_start, existing.id)
            return

        try:
            digest = generate_digest(session, period_start, period_end)
            session.commit()
            logger.info("Generated draft digest id=%d for week of %s", digest.id, period_start)
        except ValueError as e:
            logger.warning("Digest generation skipped: %s", e)
        except Exception:
            session.rollback()
            logger.exception("Unexpected error generating digest")


def scheduled_publish_and_send():
    """Publish the most recent draft digest and send to subscribers."""
    with Session(engine) as session:
        digest = session.exec(
            select(Digest)
            .where(Digest.status == DigestStatus.draft)
            .order_by(col(Digest.period_start).desc())
        ).first()

        if not digest:
            logger.info("No draft digest to publish, skipping")
            return

        try:
            digest.status = DigestStatus.published
            session.add(digest)
            session.flush()

            result = send_digest_to_subscribers(session, digest)
            session.commit()
            logger.info(
                "Published and sent digest id=%d: sent=%d, failed=%d, skipped=%d",
                digest.id, result["sent"], result["failed"], result["skipped"],
            )
        except Exception:
            session.rollback()
            logger.exception("Unexpected error publishing/sending digest id=%d", digest.id)


def start_scheduler():
    """Add jobs and start the scheduler."""
    scheduler.add_job(
        scheduled_generate,
        CronTrigger(day_of_week="sun", hour=14, minute=0),
        id="weekly_digest_generate",
        replace_existing=True,
    )
    scheduler.add_job(
        scheduled_publish_and_send,
        CronTrigger(day_of_week="tue", hour=14, minute=0),
        id="weekly_digest_send",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: generate=Sun 14:00 UTC, send=Tue 14:00 UTC")


def shutdown_scheduler():
    """Gracefully shut down the scheduler."""
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")
