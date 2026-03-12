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
from app.digest.generate import (
    generate_digest,
    generate_monthly_digest,
    get_current_month_bounds,
    get_current_week_bounds,
)
from app.digest.send import send_digest_to_subscribers
from app.models import Digest, DigestStatus, DigestType

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
            logger.info(
                "Digest already exists for week of %s (id=%d), skipping",
                period_start,
                existing.id,
            )
            return

        try:
            digest = generate_digest(session, period_start, period_end)
            session.commit()
            logger.info(
                "Generated draft digest id=%d for week of %s", digest.id, period_start
            )
        except ValueError as e:
            logger.warning("Digest generation skipped: %s", e)
        except Exception:
            session.rollback()
            logger.exception("Unexpected error generating digest")


def scheduled_monthly_generate():
    """Generate a draft monthly digest for the most recently completed month."""
    period_start, period_end = get_current_month_bounds()

    with Session(engine) as session:
        existing = session.exec(
            select(Digest)
            .where(Digest.period_start == period_start)
            .where(Digest.digest_type == DigestType.monthly)
        ).first()
        if existing:
            logger.info(
                "Monthly digest already exists for %s (id=%d), skipping",
                period_start,
                existing.id,
            )
            return

        try:
            digest = generate_monthly_digest(session, period_start, period_end)
            session.commit()
            logger.info(
                "Generated draft monthly digest id=%d for %s", digest.id, digest.title
            )
        except ValueError as e:
            logger.warning("Monthly digest generation skipped: %s", e)
        except Exception:
            session.rollback()
            logger.exception("Unexpected error generating monthly digest")


def scheduled_publish_and_send():
    """Publish all draft digests and send to subscribers."""
    with Session(engine) as session:
        drafts = session.exec(
            select(Digest)
            .where(Digest.status == DigestStatus.draft)
            .order_by(col(Digest.period_start).asc())
        ).all()

        if not drafts:
            logger.info("No draft digests to publish, skipping")
            return

        for digest in drafts:
            try:
                digest.status = DigestStatus.published
                session.add(digest)
                session.flush()

                result = send_digest_to_subscribers(session, digest)
                session.commit()
                logger.info(
                    "Published and sent digest id=%d: sent=%d, failed=%d, skipped=%d",
                    digest.id,
                    result["sent"],
                    result["failed"],
                    result["skipped"],
                )
            except Exception:
                session.rollback()
                logger.exception(
                    "Unexpected error publishing/sending digest id=%d", digest.id
                )


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
    scheduler.add_job(
        scheduled_monthly_generate,
        CronTrigger(day="1", hour=14, minute=0),
        id="monthly_digest_generate",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: weekly generate=Sun 14:00, weekly send=Tue 14:00, monthly generate=1st 14:00 UTC"
    )


def shutdown_scheduler():
    """Gracefully shut down the scheduler."""
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")
